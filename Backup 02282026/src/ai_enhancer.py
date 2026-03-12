def enhance_trend(merch):
    prompt = f"""
You are designing coffee mugs. Use the information below to generate creative content:

📝 Original Trending Post: 
{merch['trend']}

Design suggestion: {merch['design_suggestion']}
Etsy Keywords: {', '.join(merch['etsy_keywords'])}

🎨 Canva Design Ideas:
Provide 3 different ways this slogan could be laid out on a coffee mug. 
Include layout, font style, color scheme, and any small graphics/elements.
Keep it short and actionable for someone creating it in Canva.

💡 Primary & Alternate Slogans:
From the original trending post above, create 1 short, catchy PRIMARY slogan for a mug that captures the essence of the trend.
Then generate 3 clever ALT slogans based on the same trend.
Keep them funny, clever, or relatable.
Please provide output in a clear, copy-paste friendly format.
"""
    return {"prompt": prompt}
