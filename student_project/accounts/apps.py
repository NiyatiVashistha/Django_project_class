import os
import shutil
import sys
from django.apps import AppConfig
from django.conf import settings

class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        """
        EDUCATIONAL FEATURE: The ready() method is a Django application lifecycle hook 
        that is executed precisely once after all apps have been loaded. 
        It is the perfect place to run startup routines!
        """
        # Only run this sync logic during runserver so we don't bombard commands like migrate
        if 'runserver' not in sys.argv:
            return

        try:
            db_path = settings.DATABASES['default']['NAME']
            if 'backup' in settings.DATABASES:
                backup_path = settings.DATABASES['backup']['NAME']
                
                # Check if the primary database file is actually available
                if os.path.exists(db_path):
                    # Hot-copy the binary sqlite3 file to the backup location
                    shutil.copy2(db_path, backup_path)
                    print(f"[App Hook] Automatically synced primary DB to replica: {backup_path.name}")
        except Exception as e:
            print(f"[App Hook] Could not sync database: {e}")
