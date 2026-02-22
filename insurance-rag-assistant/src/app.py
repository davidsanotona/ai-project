from brain import InsuranceAssistant

def start_demo():
    print("David-Dawei Life Assistant is waking up...")
    
    # CHANGE THIS LINE: Point to your actual PDF file name
    assistant = InsuranceAssistant("../data/ying_zheng_policy.pdf") 
    
    print("\n" + "★"*40)
    print("WELCOME TO DAVID-DAWEI LIFE SUPPORT")
    print("Ask me about Policy #DD-2026-PRIME")
    print("★"*40)

    while True:
        user_query = input("\nUser: ")
        if user_query.lower() in ['exit', 'quit']: break
        
        answer = assistant.ask(user_query)
        print(f"\nAI: {answer}")

if __name__ == "__main__":
    start_demo()