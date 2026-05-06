import sys
import os
sys.path.append(os.getcwd())
from app.parser import parse_food_log

def test():
    try:
        print("Testing with regional food: Chicken Rogan Josh")
        result = parse_food_log("1 misal pav")
        print("Result:", result)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
