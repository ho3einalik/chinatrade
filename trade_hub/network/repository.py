"""
My Trade Network Repository (Private Contacts & Business Network).
Provides search, de-duplication, tagging, and priority matching for confidential contacts.
"""

from typing import List, Optional, Dict, Any
from trade_hub.db import TradeHubDatabase
from trade_hub.models import PrivateContact, TradeRole


class TradeNetworkRepository:
    def __init__(self, db: Optional[TradeHubDatabase] = None):
        self.db = db or TradeHubDatabase()

    def add_contact(self, contact: PrivateContact) -> tuple[int, bool]:
        """
        Inserts new contact with de-duplication check.
        Returns (contact_id, is_new).
        """
        existing = self.find_duplicate(contact)
        if existing:
            return (existing.id, False)

        new_id = self.db.add_contact(contact)
        self.db.log_audit("ADD_CONTACT", "PrivateContact", new_id, f"Added {contact.name} ({contact.role.value})", contact.tenant_id)
        return (new_id, True)

    def save_contact(self, contact: PrivateContact) -> PrivateContact:
        """
        Saves a contact to private network. Raises ValueError if duplicate exists.
        """
        existing = self.find_duplicate(contact)
        if existing:
            raise ValueError(f"Duplicate contact detected: '{existing.name}' already exists.")
        new_id = self.db.add_contact(contact)
        contact.id = new_id
        self.db.log_audit("ADD_CONTACT", "PrivateContact", new_id, f"Added {contact.name} ({contact.role.value})", contact.tenant_id)
        return contact

    def find_duplicate(self, contact: PrivateContact) -> Optional[PrivateContact]:
        """Checks if a contact with matching email, website, or name+country already exists."""
        all_contacts = self.db.list_contacts(tenant_id=contact.tenant_id)
        c_name = contact.name.strip().lower()
        c_email = contact.email.strip().lower() if contact.email else None
        c_web = contact.website.strip().lower().replace("https://", "").replace("http://", "").rstrip("/") if contact.website else None

        for item in all_contacts:
            if c_email and item.email and item.email.strip().lower() == c_email:
                return item
            if c_web and item.website:
                item_web = item.website.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
                if item_web == c_web and len(c_web) > 4:
                    return item
            if item.name.strip().lower() == c_name and item.country.strip().lower() == contact.country.strip().lower():
                return item
        return None

    def search_network_for_product(
        self,
        product_query: str,
        role: Optional[TradeRole] = None,
        country: Optional[str] = None,
        tenant_id: str = "default_importer"
    ) -> List[PrivateContact]:
        """
        Priority Search: Scans user's private network for matching buyers or suppliers.
        Matches against product names, tags, and HS codes.
        """
        all_c = self.db.list_contacts(role=role, country=country, tenant_id=tenant_id)
        if not product_query:
            return all_c

        tokens = [t.lower() for t in product_query.replace("-", " ").replace("_", " ").split() if len(t) > 1]
        results = []

        for c in all_c:
            score = 0
            prods_text = " ".join(c.products).lower()
            hs_text = " ".join(c.hs_codes).lower()
            name_text = c.name.lower()
            notes_text = c.private_notes.lower()

            for t in tokens:
                if t in prods_text:
                    score += 3
                if t in hs_text:
                    score += 4
                if t in name_text:
                    score += 2
                if t in notes_text:
                    score += 1

            if score > 0:
                results.append((score, c))

        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results]

    def search_contacts(
        self,
        product_query: Optional[str] = None,
        hs_code: Optional[str] = None,
        role: Optional[TradeRole] = None,
        country: Optional[str] = None,
        tenant_id: str = "default_importer"
    ) -> List[PrivateContact]:
        parts = []
        if product_query:
            parts.append(product_query)
        if hs_code:
            parts.append(hs_code)
        query = " ".join(parts)
        return self.search_network_for_product(product_query=query, role=role, country=country, tenant_id=tenant_id)

    def get_stats(self, tenant_id: str = "default_importer") -> Dict[str, int]:
        contacts = self.db.list_contacts(tenant_id=tenant_id)
        buyers = [c for c in contacts if c.role in (TradeRole.BUYER, TradeRole.BOTH)]
        suppliers = [c for c in contacts if c.role in (TradeRole.SUPPLIER, TradeRole.BOTH)]
        countries = set(c.country for c in contacts if c.country)

        return {
            "total_contacts": len(contacts),
            "buyers_count": len(buyers),
            "suppliers_count": len(suppliers),
            "active_countries_count": len(countries)
        }

    def get_network_stats(self, tenant_id: str = "default_importer") -> Dict[str, Any]:
        s = self.get_stats(tenant_id=tenant_id)
        return {
            "total_contacts": s["total_contacts"],
            "buyers": s["buyers_count"],
            "suppliers": s["suppliers_count"],
            "unique_countries_count": s["active_countries_count"]
        }
