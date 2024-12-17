from openai import OpenAI

client = OpenAI()

def get_chatgpt_response(prompt):
    try:
        '''response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{ "role": "system", "content": "You are a student from the computer science department." },
                        {"role": "user", "content": "口語一點，用50字簡答:"+prompt}]
        )'''
        response = client.chat.completions.create(
            messages=[
                { "role": "system", "content": "You are a student from the computer science department." },
                {
                    "role": "user",
                    "content": "口語一點，用50字簡答:"+prompt,
                }
            ],
            model="gpt-4o-mini",
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"ChatGPT 回應出錯: {e}")
        return "無法處理訊息"

