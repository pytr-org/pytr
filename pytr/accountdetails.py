import json

class Accountdetails:
    def __init__(self, tr):
        self.tr = tr
        self.data = None

    def get(self):
        self.data = self.tr.get_account_details()
        print(f"{self.data}")
        return self.data
    
    def data_to_file(self, output_path):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f)
    
