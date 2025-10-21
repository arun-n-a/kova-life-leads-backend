"""API endpoints related to IVR calls (Using Elevenlabs)."""

import re
import json
from typing import Optional, Tuple
from uuid import uuid4

from flask import Blueprint, jsonify, request
from openai import OpenAI

from app import redis_obj
from app.api.twilio_call_sms import extract_mortgage_id_from_text
from app.services.twilio_call_sms import (
    get_twilio_status_call_back,
    temp_twilio_mortgage_id_validation,
    twilio_call_response_incomplete,
    twilio_mortgage_id_validation,
)
from app.services.utils import add_redis_ttl_data
from config import Config_is
from constants import OPENAI_MODEL

elevenlabs_bp = Blueprint("elevenlabs", __name__)

client = OpenAI(api_key=Config_is.OPENAI_API_KEY)


@elevenlabs_bp.route("/mortgage_id_validation", methods=["POST"])
def mortgage_id_validation():
    """Endpoint to validate mortgage ID and store in Redis."""
    data = request.get_json()
    print("Received JSON data:", data)

    mortgage_id, error_msg = extract_mortgage_id_from_text(data.get("mortgage_id"))

    if not mortgage_id:
        return jsonify({"mortgage_id": "error", "message": error_msg})

    data["mortgage_id"] = mortgage_id
    add_redis_ttl_data(f"call_sid_{data.get("sid")}", 900, data)

    add_redis_ttl_data(f"MV_{uuid4().hex[:6]}", 336, data)

    response = twilio_mortgage_id_validation(data)

    return jsonify(response)


@elevenlabs_bp.route("/incomplete_response", methods=["POST"])
def elevenlabs_calling_response_incomplete():
    data = request.json
    print("Incoming data:", data)

    redis_data_raw = redis_obj.get(f'call_sid_{data["sid"]}')
    
    if not redis_data_raw:
        return jsonify({'status': 'error', 'messege': 'There is an error please try again later.'})
    
    redis_data = json.loads(redis_data_raw)

    field_mappings = {
        "number": extract_phone_number_from_text,
        "age": extract_age_from_text,
    }

    for key, extractor in field_mappings.items():
        if data.get(key):
            value, msg = extractor(data[key])
            if not value:
                return jsonify({'status': 'error', 'messege': msg})
            redis_data[key] = value

    for key in ["coborrower", "tobacco", "health"]:
        if data.get(key) is not None:
            redis_data[key] = data[key]

    add_redis_ttl_data(f'call_sid_{data["sid"]}', 300, redis_data)

    add_redis_ttl_data(f"TRI_{uuid4().hex}", 336, redis_data)

    redis_data.pop("confirm_number", None)

    print("Final data before Twilio push:", redis_data)
    twilio_call_response_incomplete(redis_data)

    print("Final response data:", redis_data)
    return jsonify({"data": redis_data, "message": "Success", "status": 200})


def extract_age_from_text(text) -> Tuple[Optional[str], str]:
    prompt = f"""
    You are a speech-to-text assistant that helps extract a person's age from noisy input.

    Instructions:
    - Extract the **age** from this text.
    - The age must be a **number between 1 and 130**.
    - Recognize spoken digits like "two two" as 22, and words like "twenty two" as 22.
    - Ignore irrelevant words like "years old", "I am", or punctuation.

    Examples:
    - Input: "I am twenty five years old" → Output: "You said 25. Is that correct?"
    - Input: "one hundred and forty" → Output: "I heard 140, which is not a valid age. Please say your age again."
    - Input: "blah blah" → Output: "Sorry, I didn’t catch a valid age."

    Now extract and validate from:

    Text: "{text}"

    Only respond with:
    - "You said {{age}}. Is that correct?" (for valid age)
    - "I heard {{age}}, which is not a valid age. Please say your age again."
    - "Sorry, I didn’t catch a valid age."
    """
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        content = response.choices[0].message.content.strip()
        print("OpenAI raw response:", content)
        digits = re.findall(r"\b\d+\b", content)
        age = int(digits[0]) if digits else None

        if not digits:
            return None, "Sorry, I didn’t catch a valid age."

        if age < 1 or age > 130:
            return None, f"I heard {age}, which is not a valid age."

        return age, f"You said {age}. Is that correct?"

    except Exception as e:
        print("OpenAI extraction error:", e)
        return None, "Sorry, I'm having trouble processing your response. Please try again."


def extract_phone_number_from_text(text) -> Tuple[Optional[str], str]:
    prompt = f"""
    You are a voice-to-text cleanup assistant.

    Your task is to extract **only digits** from user speech that contains a phone number.
    - Convert spoken number words to digits. (e.g., "nine one seven" → 917)
    - Handle patterns like "double two" → "22", "triple five" → "555"
    - Ignore extra symbols like slashes, commas, or words unrelated to numbers.
    - Keep the full number as-is, even if more or less than 10 digits.

    Examples:
    - Input: "My number is nine eight zero double four one triple six two"
      Output: "9804416662"

    - Input: "Call me at one two three slash four five six"
      Output: "123456"

    - Input: "Sorry, I don’t want to share it"
      Output: "INVALID"

    Now extract the phone number from this input:
    "{text}"

    Respond with just the digits (like: 9876543210) or the word INVALID if no number is found.
    """
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = response.choices[0].message.content.strip()
        print("OpenAI raw phone output:", content)

        digits = re.sub(r"[^0-9]", "", content)
        if not digits:
            return None, "Sorry, I couldn't understand any digits."
        return digits, f"You said {', '.join(digits)}. Is that correct?"

    except Exception as e:
        print("OpenAI phone number extraction error:", e)
        return None, "Sorry, I had trouble understanding. Please try saying your phone number again."


# Currently not using this function. This is for future use
def extract_yes_or_no_from_text(text) -> Tuple[Optional[str], str]:
    prompt = f"""
    You are an intelligent assistant that interprets a person's spoken response to a yes-or-no question.

    Instructions:
    - Understand common ways people say YES or NO, including repeated or casual variations:
      - YES: "yes", "yeah", "yup", "sure", "of course", "definitely", "okay", "affirmative", "yes yes", "yeah yeah", etc.
      - NO: "no", "nope", "nah", "not really", "no way", "never", "no no", "nah nah", etc.
    - Normalize repeated phrases — "yes yes", "no no", etc. — and treat them as single YES or NO.
    - If both YES and NO appear in the same message (e.g., "yes no", "maybe yes but also no"), then treat as unclear.
    - Ignore filler words like "um", "well", "you know", etc.
    - If the response clearly means yes, respond: **YES**
    - If it clearly means no, respond: **NO**
    - If it’s unclear, contradictory, or includes both YES and NO, respond: **UNSURE**

    User said: "{text}"

    Respond with one word only: YES, NO, or UNSURE
    """
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        result = response.choices[0].message.content.strip().upper()
        if result == "YES":
            return "1", "You said Yes. Thank you for your response."
        elif result == "NO":
            return "2", "You said No. Thank you for your response."
        else:
            return None, "Sorry, I didn’t understand clearly."

    except Exception as e:
        print("OpenAI error:", e)
        return None, "I'm sorry, I didn't quite catch that. Could you please say that again?"
