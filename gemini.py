from google import genai
from google.genai import types
import config
GEMINI_API_KEY = config.GEMINI_API_KEY

client = genai.Client(api_key = GEMINI_API_KEY)

def generate_response(prompt):
    
    response = client.models.generate_content(
        model='gemini-2.5-flash-preview-05-20',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction='あなたは物知りな昭和レトロな世話焼きおばあちゃんです。「トモさん」と回りからは呼ばれています。同級生の男の子からの質問に答えてください。回答は200字以内でお願いします。',
            top_p= 0.5,
            temperature= 0.5,
            response_mime_type='text/plain'
        ),
    )
    return response.text

if __name__ == '__main__':
    user_prompt = "ねえ、トモさん、明日の天気ってどう思う？私、気になっちゃうんだ…"
    response_text = generate_response(user_prompt)
    print("トモさん:")
    print(response_text)

    user_prompt_2 = "最近、何か面白いことあった？教えてよ。"
    response_text_2 = generate_response(user_prompt_2)
    print("\nトモさん:")
    print(response_text_2)
    