from transformers import MarianMTModel, MarianTokenizer
from sacrebleu.metrics import BLEU
import torch
import os
os.environ['TRANSFORMERS_NO_TF'] = '1'


class HSKTranslator:
    def __init__(self, model_folder="../hsk_model"):
        import os
        abs_path = os.path.abspath(model_folder)
        print(f"Loading HSK-tuned model from: {abs_path}")
        
        self.tokenizer = MarianTokenizer.from_pretrained(abs_path, local_files_only=True)
        self.model = MarianMTModel.from_pretrained(
            abs_path, 
            local_files_only=True, 
            ignore_mismatched_sizes=True
        )

    def translate(self, text):
        # 1. Tokenize the input string
        inputs = self.tokenizer(text, return_tensors="pt", padding=True)
        
        # 2. Generate the translation tokens
        with torch.no_grad():
            translated = self.model.generate(**inputs)
            
        # 3. Decode tokens back into a string
        return self.tokenizer.decode(translated[0], skip_special_tokens=True)


def evaluate_performance(self, references, hypotheses):
    """
    Calculates the actual BLEU score for a batch of translations.
    references: List of strings (The Human HSK translations)
    hypotheses: List of strings (Model's outputs)
    """
    bleu = BLEU()
    
    # SacreBLEU expects references to be a list of lists
    score = bleu.corpus_score(hypotheses, [references])
    
    return {
        "score": score.score, # The 0-100 value
        "details": score.format() # Statistical breakdown
    }

if __name__ == "__main__":
    translator = HSKTranslator()
    
    mandarin_input = "我正在学习汉语。"  # "I am studying Chinese."
    result = translator.translate(mandarin_input)
    
    print(f"\nSource: {mandarin_input}")
    print(f"Translation: {result}")
    
    # Showcase BLEU Score evaluation 
    metrics = translator.evaluate_performance("I am studying Chinese.", result)
    print(f"Metrics: {metrics}")