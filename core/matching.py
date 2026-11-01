"""
Product Matching and Normalization Engine.
Extracts structured technical specifications, standardizes units, and performs
explainable similarity matching classified into:
- EXACT (تطبیق دقیق)
- CLOSE_WITH_DIFFERENCES (تطبیق نزدیک با تفاوت‌های مشخص)
- WEAK (تطبیق ضعیف / ریسک مغایرت بالا)
- INSUFFICIENT_DATA (داده ناکافی / نیازمند استعلام تکمیلی)
"""

import re
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

class MatchClassification(str, Enum):
    EXACT = "EXACT"                                     # تطبیق دقیق
    CLOSE_WITH_DIFFERENCES = "CLOSE_WITH_DIFFERENCES"   # تطبیق نزدیک با ذکر تفاوت‌ها
    WEAK = "WEAK"                                       # تطبیق ضعیف
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"             # داده ناکافی

class StandardUnits:
    @staticmethod
    def normalize_weight_kg(val: float, unit: str) -> float:
        """Converts grams, milligrams, tons, pounds, or ounces to standard Kilograms (kg)."""
        u = unit.lower().strip()
        if u in ("g", "gr", "گرم", "gram", "grams"):
            return val / 1000.0
        if u in ("mg", "میلی گرم"):
            return val / 1000000.0
        if u in ("ton", "tonne", "تن"):
            return val * 1000.0
        if u in ("lb", "lbs", "پوند"):
            return val * 0.45359237
        if u in ("oz", "اونس"):
            return val * 0.0283495
        return val # default kg

    @staticmethod
    def normalize_dimension_cm(val: float, unit: str) -> float:
        """Converts mm, meters, or inches to Centimeters (cm)."""
        u = unit.lower().strip()
        if u in ("mm", "میلی متر"):
            return val / 10.0
        if u in ("m", "متر", "meter"):
            return val * 100.0
        if u in ("inch", "in", "اینچ"):
            return val * 2.54
        return val # default cm

    @staticmethod
    def calculate_cbm(length_cm: float, width_cm: float, height_cm: float) -> float:
        """Calculates Cubic Meters (CBM) from dimensions in centimeters."""
        return (length_cm * width_cm * height_cm) / 1000000.0

    @staticmethod
    def normalize_battery_mah(val: float, unit: str) -> float:
        """Converts Ah or Wh to mAh assuming nominal 3.7V lithium cell."""
        u = unit.lower().strip()
        if u in ("ah", "آمپر ساعت"):
            return val * 1000.0
        if u in ("wh", "وات ساعت"):
            return (val / 3.7) * 1000.0
        return val # default mAh

    @staticmethod
    def normalize_power_watt(val: float, unit: str) -> float:
        """Converts kW or HP to Watts."""
        u = unit.lower().strip()
        if u in ("kw", "کیلووات"):
            return val * 1000.0
        if u in ("hp", "اسب بخار"):
            return val * 745.7
        return val # default Watt


class ProductSpecs(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    category: str = "general"
    weight_kg: Optional[float] = None
    volume_cbm: Optional[float] = None
    material: Optional[str] = None
    power_watts: Optional[float] = None
    voltage_volts: Optional[float] = None
    capacity_mah: Optional[float] = None
    purity_percent: Optional[float] = None
    grade: Optional[str] = None
    key_features: List[str] = Field(default_factory=list)
    raw_specs: Dict[str, Any] = Field(default_factory=dict)


class MatchExplanation(BaseModel):
    score: float = Field(..., description="Explainable matching score between 0.0 and 100.0")
    classification: MatchClassification
    pros: List[str] = Field(default_factory=list, description="نقاط قوت و تطابق مشخصات")
    cons: List[str] = Field(default_factory=list, description="مغایرت‌ها و تفاوت‌های مشخصات")
    missing_critical_attributes: List[str] = Field(default_factory=list, description="ویژگی‌های مهم نامشخص")
    is_conditional: bool = Field(default=False, description="آیا نتیجه مشروط به استعلام تکمیلی است")
    user_confirmed: Optional[bool] = None


class ProductMatchingEngine:
    """
    Evaluates semantic and technical correspondence between an Iranian market product
    and a candidate Chinese factory product.
    """

    # Canonical feature map (English and Persian synonyms mapped to unified keys)
    FEATURE_SYNONYMS = {
        "amoled": "amoled",
        "امولد": "amoled",
        "ضد آب": "waterproof",
        "waterproof": "waterproof",
        "ip68": "waterproof",
        "ip67": "waterproof",
        "bluetooth": "bluetooth",
        "بلوتوث": "bluetooth",
        "brushless": "brushless",
        "براشلس": "brushless",
        "fast charge": "fast_charge",
        "فست شارژ": "fast_charge",
        "anc": "active_noise_cancelling",
        "نویز کنسلینگ": "active_noise_cancelling",
        "gps": "gps",
        "جی پی اس": "gps"
    }

    def extract_specs_from_text(self, text: str, category: str = "general") -> ProductSpecs:
        """Heuristically extracts key technical specifications from product titles and descriptions."""
        t = text.lower()
        specs = ProductSpecs(category=category)
        cat_lower = category.lower()

        is_chem = any(k in cat_lower for k in ["مواد اولیه", "پتروشیمی", "شیمیایی", "chemical", "polymer", "resin"])
        is_elec = any(k in cat_lower for k in ["گجت", "الکترونیک", "ساعت", "موبایل", "electronics", "gadget", "watch"])
        is_tool = any(k in cat_lower for k in ["ابزار", "موتور", "پمپ", "tool", "industrial"])

        # 1. Model numbers (alphanumeric like T1000, T900, Pro 4, Ultra 2)
        if not is_chem:
            model_match = re.search(r'\b(t\d{3,4}(?:\s*ultra)?|ultra\s*\d*|pro\s*\d*|max\s*\d*|series\s*\d*|[a-z]{1,3}-\d{2,4}[a-z]?)\b', t)
            if model_match:
                specs.model = model_match.group(1).upper()

        # 2. Battery capacity (e.g. 20000mah, 5000 mah, 300mah)
        bat_match = re.search(r'(\d+[\d,.]*)\s*(mah|میلی\s*آمپر)', t)
        if bat_match:
            try:
                specs.capacity_mah = float(bat_match.group(1).replace(',', ''))
            except ValueError:
                pass

        # 3. Voltage (e.g. 21v, 12v, 220v)
        volt_match = re.search(r'(\d+[\d,.]*)\s*(v|ولت)', t)
        if volt_match:
            try:
                specs.voltage_volts = float(volt_match.group(1).replace(',', ''))
            except ValueError:
                pass

        # 4. Power (e.g. 65w, 100w, 1500w)
        watt_match = re.search(r'(\d+[\d,.]*)\s*(w|وات)', t)
        if watt_match:
            try:
                specs.power_watts = float(watt_match.group(1).replace(',', ''))
            except ValueError:
                pass

        # 5. Chemical Grade / Purity
        purity_match = re.search(r'(\d{2,3}(?:\.\d+)?)\s*%', t)
        if purity_match:
            try:
                specs.purity_percent = float(purity_match.group(1))
            except ValueError:
                pass

        # Specific Grade identification (e.g. S-65, S-70, 52518, HDPE 7000F)
        grade_code_match = re.search(r'\b(s-?\d{2,3}|[a-z]{1,4}-?\d{3,5}[a-z]?|grade\s*[a-z0-9]+)\b', t)
        if grade_code_match and (is_chem or "s-" in t or "grade" in t):
            specs.grade = grade_code_match.group(1).upper()
        elif is_chem:
            polymer_match = re.search(r'\b(hdpe|lldpe|ldpe|pvc|pp|pet|abs|pom|ps)\b', t)
            if polymer_match:
                specs.grade = polymer_match.group(1).upper()

        # 6. Canonical features
        extracted_features = set()
        for kw, canonical in self.FEATURE_SYNONYMS.items():
            if kw in t:
                extracted_features.add(canonical)
        specs.key_features = list(extracted_features)

        return specs

    def compare_products(
        self,
        iran_title: str,
        iran_specs_dict: Optional[Dict[str, Any]],
        china_title: str,
        china_specs_dict: Optional[Dict[str, Any]],
        category: str = "general"
    ) -> MatchExplanation:
        """
        Executes an explainable, category-aware comparison across model, capacity, voltage, features, and grade.
        Produces explicit MatchExplanation with pros, cons, and confidence.
        """
        iran_specs = self.extract_specs_from_text(f"{iran_title} {str(iran_specs_dict or '')}", category)
        china_specs = self.extract_specs_from_text(f"{china_title} {str(china_specs_dict or '')}", category)

        cat_lower = category.lower()
        is_chem = any(k in cat_lower for k in ["مواد اولیه", "پتروشیمی", "شیمیایی", "chemical", "polymer", "resin"])
        is_elec = any(k in cat_lower for k in ["گجت", "الکترونیک", "ساعت", "موبایل", "electronics", "gadget", "watch"])
        is_tool = any(k in cat_lower for k in ["ابزار", "موتور", "پمپ", "tool", "industrial"])

        pros: List[str] = []
        cons: List[str] = []
        missing: List[str] = []
        points = 0.0
        max_possible_points = 0.0

        has_any_iran = bool(iran_specs.model or iran_specs.grade or iran_specs.capacity_mah or iran_specs.voltage_volts or iran_specs.power_watts or iran_specs.key_features)
        has_any_china = bool(china_specs.model or china_specs.grade or china_specs.capacity_mah or china_specs.voltage_volts or china_specs.power_watts or china_specs.key_features)

        if not has_any_iran or not has_any_china:
            missing.append("هیچ مشخصه فنی، کد مدل یا استاندارد قابل استخراجی در یکی از کالاها یافت نشد")
            return MatchExplanation(
                score=35.0,
                classification=MatchClassification.INSUFFICIENT_DATA,
                pros=["تنها ارتباط متنی عمومی وجود دارد"],
                cons=[],
                missing_critical_attributes=missing,
                is_conditional=True
            )

        if is_chem:
            # Category: Chemicals & Polymers
            # 1. Grade matching (Weight: 60)
            max_possible_points += 60.0
            if iran_specs.grade and china_specs.grade:
                clean_i = iran_specs.grade.replace("-", "").replace(" ", "")
                clean_c = china_specs.grade.replace("-", "").replace(" ", "")
                if clean_i == clean_c:
                    points += 60.0
                    pros.append(f"گرید و کد ماده اولیه کاملاً یکسان است: {iran_specs.grade}")
                else:
                    cons.append(f"مغایرت اساسی در گرید: بازار ایران '{iran_specs.grade}' در برابر تأمین‌کننده چین '{china_specs.grade}'")
            elif iran_specs.grade or china_specs.grade:
                missing.append("گرید پتروشیمی/شیمیایی در یکی از منابع ذکر نشده است")
                points += 20.0
            else:
                missing.append("گرید مشخصی استخراج نشد")
                points += 25.0

            # 2. Purity (Weight: 40)
            max_possible_points += 40.0
            if iran_specs.purity_percent and china_specs.purity_percent:
                if abs(iran_specs.purity_percent - china_specs.purity_percent) <= 0.5:
                    points += 40.0
                    pros.append(f"درصد خلوص منطبق است ({iran_specs.purity_percent}%)")
                else:
                    cons.append(f"مغایرت در درصد خلوص: {iran_specs.purity_percent}% در برابر {china_specs.purity_percent}%")
            else:
                points += 25.0

        elif is_elec:
            # Category: Gadgets & Consumer Electronics
            # 1. Model / Series matching (Weight: 45)
            max_possible_points += 45.0
            if iran_specs.model and china_specs.model:
                clean_i = iran_specs.model.replace("-", "").replace(" ", "")
                clean_c = china_specs.model.replace("-", "").replace(" ", "")
                if clean_i == clean_c:
                    points += 45.0
                    pros.append(f"کد مدل کاملاً منطبق است: {iran_specs.model}")
                elif clean_i in clean_c or clean_c in clean_i:
                    points += 35.0
                    pros.append(f"کد مدل مشابهت زیادی دارد: {iran_specs.model} در برابر {china_specs.model}")
                else:
                    cons.append(f"مغایرت و اختلاف در کد مدل: مدل بازار ایران '{iran_specs.model}' اما تأمین‌کننده چین '{china_specs.model}' است.")
            else:
                missing.append("کد مدل صریح در عنوان یکی از کالاها یافت نشد")
                points += 20.0

            # 2. Key Features (Weight: 35)
            max_possible_points += 35.0
            common_features = set(iran_specs.key_features).intersection(set(china_specs.key_features))
            if common_features:
                points += min(35.0, 20.0 + len(common_features) * 7.5)
                pros.append(f"ویژگی‌های برجسته مشترک: {', '.join(common_features)}")
            else:
                points += 15.0

            # 3. Technical parameters (Capacity/Battery/Watts) (Weight: 20)
            max_possible_points += 20.0
            if iran_specs.capacity_mah and china_specs.capacity_mah:
                ratio = min(iran_specs.capacity_mah, china_specs.capacity_mah) / max(iran_specs.capacity_mah, china_specs.capacity_mah)
                if ratio >= 0.90:
                    points += 20.0
                    pros.append(f"ظرفیت باتری منطبق است ({iran_specs.capacity_mah:.0f} mAh)")
                else:
                    cons.append(f"مغایرت در ظرفیت باتری: {iran_specs.capacity_mah:.0f} mAh در برابر {china_specs.capacity_mah:.0f} mAh")
            else:
                points += 15.0

        elif is_tool:
            # Category: Industrial & Power Tools
            # 1. Voltage / Power (Weight: 45)
            max_possible_points += 45.0
            if iran_specs.voltage_volts and china_specs.voltage_volts:
                if abs(iran_specs.voltage_volts - china_specs.voltage_volts) < 1.0:
                    points += 45.0
                    pros.append(f"ولتاژ کاری دقیقاً منطبق است ({iran_specs.voltage_volts:.0f}V)")
                else:
                    cons.append(f"مغایرت در ولتاژ کاری: {iran_specs.voltage_volts}V در برابر {china_specs.voltage_volts}V")
            elif iran_specs.power_watts and china_specs.power_watts:
                if abs(iran_specs.power_watts - china_specs.power_watts) < 20.0:
                    points += 45.0
                    pros.append(f"توان الکتریکی منطبق است ({iran_specs.power_watts:.0f}W)")
                else:
                    cons.append(f"مغایرت در توان مصرفی: {iran_specs.power_watts}W در برابر {china_specs.power_watts}W")
            else:
                points += 20.0

            # 2. Key Features (Brushless, Impact, Dual Speed) (Weight: 35)
            max_possible_points += 35.0
            common = set(iran_specs.key_features).intersection(set(china_specs.key_features))
            if common:
                points += min(35.0, 25.0 + len(common) * 5.0)
                pros.append(f"ویژگی‌های مشترک ابزار: {', '.join(common)}")
            else:
                points += 15.0

            # 3. Model / Type (Weight: 20)
            max_possible_points += 20.0
            if iran_specs.model and china_specs.model:
                if iran_specs.model.replace("-", "") == china_specs.model.replace("-", ""):
                    points += 20.0
                    pros.append(f"کد مدل منطبق است: {iran_specs.model}")
                else:
                    cons.append(f"مغایرت در کد مدل ابزار: {iran_specs.model} در برابر {china_specs.model}")
            else:
                points += 15.0

        else:
            # General
            max_possible_points += 40.0
            if iran_specs.model and china_specs.model:
                if iran_specs.model.replace("-", "") == china_specs.model.replace("-", ""):
                    points += 40.0
                    pros.append(f"کد مدل منطبق است: {iran_specs.model}")
                else:
                    cons.append(f"مغایرت در کد مدل: {iran_specs.model} در برابر {china_specs.model}")
            else:
                points += 20.0

            max_possible_points += 30.0
            if iran_specs.voltage_volts and china_specs.voltage_volts:
                if abs(iran_specs.voltage_volts - china_specs.voltage_volts) < 1.0:
                    points += 30.0
                    pros.append(f"ولتاژ کاری منطبق است ({iran_specs.voltage_volts:.0f}V)")
                else:
                    cons.append(f"مغایرت در ولتاژ کاری: {iran_specs.voltage_volts}V در برابر {china_specs.voltage_volts}V")
            elif iran_specs.power_watts and china_specs.power_watts:
                if abs(iran_specs.power_watts - china_specs.power_watts) < 10.0:
                    points += 30.0
                    pros.append(f"توان الکتریکی منطبق است ({iran_specs.power_watts:.0f}W)")
                else:
                    cons.append(f"مغایرت در توان مصرفی: {iran_specs.power_watts}W در برابر {china_specs.power_watts}W")
            else:
                points += 20.0

            max_possible_points += 30.0
            common = set(iran_specs.key_features).intersection(set(china_specs.key_features))
            if common:
                points += min(30.0, 15.0 + len(common) * 7.5)
                pros.append(f"ویژگی‌های مشترک: {', '.join(common)}")
            else:
                points += 15.0

        # Calculate final percentage
        final_score = round((points / max_possible_points) * 100.0, 1) if max_possible_points > 0 else 50.0

        # Classification decision
        if final_score >= 80.0 and len(cons) == 0:
            classification = MatchClassification.EXACT
            is_conditional = False
        elif (final_score >= 55.0 and len(cons) <= 1) or (final_score >= 70.0):
            classification = MatchClassification.CLOSE_WITH_DIFFERENCES
            is_conditional = True
        elif len(missing) >= 3 and final_score < 50.0:
            classification = MatchClassification.INSUFFICIENT_DATA
            is_conditional = True
        else:
            classification = MatchClassification.WEAK
            is_conditional = True

        return MatchExplanation(
            score=final_score,
            classification=classification,
            pros=pros if pros else ["تشابه عمومی در حوزه کالا"],
            cons=cons,
            missing_critical_attributes=missing,
            is_conditional=is_conditional
        )
