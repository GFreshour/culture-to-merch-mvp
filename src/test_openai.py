from ai_insights import analyze_trend

if __name__ == "__main__":
    print("🧠 Testing OpenAI on a single trend...\n")

    trend_title = "Brave Little Soldiers vs Ruthless Giants"
    context = "Underdog humor, meme format, relatable workplace energy"

    result = analyze_trend(trend_title, context)

    print("===== AI OUTPUT =====")
    print(result)
    print("=====================")
