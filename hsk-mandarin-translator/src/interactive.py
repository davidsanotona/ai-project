# src/interactive.py
from translator import HSKTranslator

def main():
    # Pass the folder path, not the direction keyword
    translator = HSKTranslator(model_folder="../hsk_model")
    
    print("\n" + "="*40)
    print("AI MANDARIN to ENGLISH TRANSLATOR ACTIVE")
    print("Type 'exit' to stop the session")
    print("="*40)
    
    while True:
        user_input = input("\nEnter Mandarin text: ")
        if user_input.lower() == 'exit':
            break
        
        result = translator.translate(user_input)
        print(f"English: {result}")

if __name__ == "__main__":
    main()