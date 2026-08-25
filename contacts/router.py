class ContactDatabaseRouter:
    app_label = "contacts"
    def db_for_read(self, model, **hints): return "contacts" if model._meta.app_label == self.app_label else None
    def db_for_write(self, model, **hints): return "contacts" if model._meta.app_label == self.app_label else None
    def allow_relation(self, obj1, obj2, **hints):
        if self.app_label in {obj1._meta.app_label, obj2._meta.app_label}: return obj1._meta.app_label == obj2._meta.app_label
        return None
    def allow_migrate(self, db, app_label, **hints):
        return db == "contacts" if app_label == self.app_label else db != "contacts"
