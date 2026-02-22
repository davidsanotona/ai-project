import os
os.environ['TRANSFORMERS_NO_TF'] = '1'

import pandas as pd
from sacrebleu.metrics import BLEU
from translator import HSKTranslator

def run_hsk_validation():
    # 1. Initialize the AI
    translator = HSKTranslator()
    bleu = BLEU()

    # 2. Samples
    validation_set = [
        {"zh": "我喜欢喝茶。", "en": "I like to drink tea."},
        {"zh": "他在哪儿？", "en": "Where is he?"},
        {"zh": "这是我的老师。", "en": "This is my teacher."},
        {"zh": "我想去北京。", "en": "I want to go to Beijing."},
        {"zh": "今天天气很好。", "en": "The weather is good today."},
        {"zh": "你会说英语吗？", "en": "Can you speak English?"},
        {"zh": "请给我一杯水。", "en": "Please give me a cup of water."},
        {"zh": "她在医院 work。", "en": "She works at the hospital."},
        {"zh": "我有一个猫。", "en": "I have a cat."},
        {"zh": "我们是好朋友。", "en": "We are good friends."}
    ]

    # 3. Generate Predictions (Hypotheses)
    print("\n--- Running HSK Inference ---")
    sources = [item['zh'] for item in validation_set]
    references = [item['en'] for item in validation_set]
    hypotheses = [translator.translate(s) for s in sources]

    # 4. Calculate Real Metrics
    score = bleu.corpus_score(hypotheses, [references])
    
    # 5. Export Results for Presentation
    report = pd.DataFrame({
        "Mandarin_Source": sources,
        "Human_Reference": references,
        "AI_Translation": hypotheses
    })

    # --- Path Logic ---
    script_path = os.path.abspath(__file__) 
    src_dir = os.path.dirname(script_path)
    project_root = os.path.dirname(src_dir)
    output_dir = os.path.join(project_root, 'output')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created missing directory: {output_dir}")

    csv_file_path = os.path.join(output_dir, 'hsk_validation_report.csv')

    report.to_csv(csv_file_path, index=False)

    print("\n" + "="*40)
    print("SUCCESS!")
    print(f"Report saved at: {csv_file_path}")
    print(f"Final BLEU Score: {score.score:.2f}")
    print("="*40)

if __name__ == "__main__":
    run_hsk_validation()