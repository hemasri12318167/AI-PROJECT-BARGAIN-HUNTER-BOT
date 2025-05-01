from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ✅ Add your keys
GENAI_KEY = "AIzaSyAZh3zEFd5InH4ZoWrQkFDXzrel5zP32cg"
SERPAPI_KEY = "cee3a34f45f0f6240635fa476b9d9a78535bf40fb7beb98664749d098ed0f0ef"

genai.configure(api_key=GENAI_KEY)
gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# 🔍 Function to get price from Amazon
def get_amazon_price(query):
    try:
        params = {
            "engine": "amazon",
            "amazon_domain": "amazon.in",
            "gl": "in",
            "hl": "en",
            "api_key": SERPAPI_KEY,
            "search_term": query
        }
        res = requests.get("https://serpapi.com/search", params=params)
        data = res.json()

        results = data.get("shopping_results")
        if not results:
            return None

        product = results[0]
        title = product.get("title", "No Title")
        price = product.get("price")
        link = product.get("link", "#")

        if price:
            return f"🛍️ Bargain Hunter says:\n🔍 {title}\n💰 Price: {price}\n🔗 Link: {link}"
        else:
            return f"🔍 {title}\n⚠️ Sorry, price not found. Check manually: {link}"

    except Exception as e:
        logging.exception("Error fetching Amazon price:")
        return None

# 🔄 Fallback: Flipkart Scraper (experimental)
def get_flipkart_price(query):
    try:
        params = {
            "engine": "google",
            "q": f"{query} site:flipkart.com",
            "api_key": SERPAPI_KEY
        }
        res = requests.get("https://serpapi.com/search", params=params)
        data = res.json()
        link = None

        for result in data.get("organic_results", []):
            if "flipkart.com" in result.get("link", ""):
                link = result["link"]
                break

        if link:
            return f"🛍️ Couldn't find on Amazon.\nBut you can try this Flipkart link:\n🔗 {link}"
        else:
            return "❌ No results found on Flipkart either."

    except Exception as e:
        logging.exception("Error fetching Flipkart fallback:")
        return "⚠️ Something went wrong during Flipkart lookup."

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/gemini_query', methods=['POST'])
def gemini_query():
    data = request.get_json()
    query = data.get('query', '')

    try:
        intent_prompt = f"""
Classify the user query into one of the following:
- BARGAIN_QUERY: if it's asking for a product under a price
- GENERAL_CHAT: if it's a greeting or general question
- OTHER

Only reply with one label.

User Query: {query}
"""
        intent_response = gemini_model.generate_content(intent_prompt)
        intent = intent_response.text.strip().upper()

        logging.info(f"Intent Detected: {intent}")

        if "BARGAIN_QUERY" in intent:
            response = get_amazon_price(query)
            if not response:
                response = get_flipkart_price(query)
            return jsonify({'response': response})

        elif "GENERAL_CHAT" in intent:
            chat_response = gemini_model.generate_content(f"You are a friendly shopping assistant. Reply to: {query}")
            return jsonify({'response': chat_response.text.strip()})

        else:
            return jsonify({'response': "🤖 Sorry, I can only help with shopping deals or general chat!"})

    except Exception as e:
        logging.exception("Gemini processing error:")
        return jsonify({'response': "⚠️ Something went wrong. Please try again later."})

if __name__ == '__main__':
    app.run(debug=True)
