import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Always convert Decimal to string (not float!)
            return str(obj)
        return super().default(obj)
