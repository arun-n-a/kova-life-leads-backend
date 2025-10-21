"""API Endpoints related to IVR calls and SMS."""
import re
from typing import Optional, Tuple
from uuid import uuid4

from flask import Blueprint, jsonify, request
from openai import OpenAI

from config import Config_is
from constants import OPENAI_MODEL
from app.services.twilio_call_sms import (
    twilio_mortgage_id_validation,
    get_twilio_status_call_back,
    twilio_call_response_incomplete,
    temp_twilio_mortgage_id_validation,
    temp_twilio_mortgage_id_validation_for_file
)
from app.services.utils import add_redis_ttl_data

twilio_bp = Blueprint("twilio webhook", __name__)


@twilio_bp.route("/mortgage_validation", methods=["POST"])
def twilio_id_validation():
    """
    Validate Mortgage ID from Twilio Call

    Receives form data via POST and validates a mortgage ID by checking against internal records.
    It returns borrower details, bank info, and a redirect URL if the ID is valid.

    ---
    tags:
      - Twilio
    summary: Validate Mortgage ID
    description: >
      This endpoint is used during Twilio calls to validate a mortgage ID
      against stored lead data. Returns lead details and a URL if valid.


    parameters:
      - name: mortgage_id
        in: formData
        type: string
        required: true
        description: Mortgage ID to be validated.
      - name: ani
        in: formData
        type: string
        required: false
        description: Automatic Number Identification (caller phone number).
    responses:
      200:
        description: Validation result with lead details
        schema:
          type: object
          properties:
            name:
              type: string
              example: Sam Michael
            mortgage_id:
              type: string
              example: 12345
            bank:
              type: string
              example: ABC Bank
            source:
              type: string
              example: Lead Source Name
            url:
              type: string
              example: https://frontend.example.com/single-mortgage-public/12345/abcde12345
            state:
              type: string
              example: IA
    """
    
    if request.is_json:
        data = request.get_json()  # The request from Elevenlabs
        print('json data:', data)
        mort, msg = extract_mortgage_id_from_text(data.get('mortgage_id'))
        print('open ai response:', mort, msg)
        if mort:
            data['mortgage_id'] = mort
        else:
            return jsonify({'mortgage_id': 'error', 'message': msg})
    else:
        data = request.form.to_dict() # request from Twilio Studio
        print('form data:', data)
    # result = {
    #     'name': 'Sam Michael', 'status': 'valid', 
    #     'message': 'Success', 'bank': 'ABC Bank', 
    #     'date': '10-20-2023', 'url': '', 'state': 'IA'}
    # return jsonify(result)
    print(data)
    add_redis_ttl_data(f"MV_{data['sid']}_{uuid4().hex[:6]}", 336, data)
    data = twilio_mortgage_id_validation(data)
    print(data)
    return jsonify(data)

# TODO: delete it after sometime
@twilio_bp.route("/mortgage_validation_temp", methods=["POST"])
def twilio_id_validation_temp():
    """
    Validate Mortgage ID from Twilio Call

    Receives form data via POST and validates a mortgage ID by checking against internal records.
    It returns borrower details, bank info, and a redirect URL if the ID is valid.

    ---
    tags:
      - Twilio
    summary: Validate Mortgage ID
    description: >
      This endpoint is used during Twilio calls to validate a mortgage ID
      against stored lead data. Returns lead details and a URL if valid.


    parameters:
      - name: mortgage_id
        in: formData
        type: string
        required: true
        description: Mortgage ID to be validated.
      - name: ani
        in: formData
        type: string
        required: false
        description: Automatic Number Identification (caller phone number).
    responses:
      200:
        description: Validation result with lead details
        schema:
          type: object
          properties:
            name:
              type: string
              example: Sam Michael
            mortgage_id:
              type: string
              example: 12345
            bank:
              type: string
              example: ABC Bank
            source:
              type: string
              example: Lead Source Name
            url:
              type: string
              example: https://frontend.example.com/single-mortgage-public/12345/abcde12345
            state:
              type: string
              example: IA
    """
    data = request.form.to_dict()
    # result = {
    #     'name': 'Sam Michael', 'status': 'valid', 
    #     'message': 'Success', 'bank': 'ABC Bank', 
    #     'date': '10-20-2023', 'url': '', 'state': 'IA'}
    # return jsonify(result)
    print(data)
    add_redis_ttl_data(f"MV_{data['sid']}_{uuid4().hex[:6]}", 336, data)
    data = temp_twilio_mortgage_id_validation(data)
    print(data)
    return jsonify(data)


# TODO: delete it after sometime
@twilio_bp.route("/mortgage_validation_temp/<int:file_id>", methods=["POST"])
def twilio_id_validation_temp_(file_id: int):
    """
    Validate Mortgage ID from Twilio Call

    Receives form data via POST and validates a mortgage ID by checking against internal records.
    It returns borrower details, bank info, and a redirect URL if the ID is valid.

    ---
    tags:
      - Twilio
    summary: Validate Mortgage ID
    description: >
      This endpoint is used during Twilio calls to validate a mortgage ID
      against stored lead data. Returns lead details and a URL if valid.


    parameters:
      - name: mortgage_id
        in: formData
        type: string
        required: true
        description: Mortgage ID to be validated.
      - name: ani
        in: formData
        type: string
        required: false
        description: Automatic Number Identification (caller phone number).
    responses:
      200:
        description: Validation result with lead details
        schema:
          type: object
          properties:
            name:
              type: string
              example: Sam Michael
            mortgage_id:
              type: string
              example: 12345
            bank:
              type: string
              example: ABC Bank
            source:
              type: string
              example: Lead Source Name
            url:
              type: string
              example: https://frontend.example.com/single-mortgage-public/12345/abcde12345
            state:
              type: string
              example: IA
    """
    data = request.form.to_dict()
    # result = {
    #     'name': 'Sam Michael', 'status': 'valid', 
    #     'message': 'Success', 'bank': 'ABC Bank', 
    #     'date': '10-20-2023', 'url': '', 'state': 'IA'}
    # return jsonify(result)
    print(data)
    add_redis_ttl_data(f"MV_{data['sid']}_{uuid4().hex[:6]}", 336, data)
    data = temp_twilio_mortgage_id_validation_for_file(data, file_id)
    print(data)
    return jsonify(data)


@twilio_bp.route("/voice_status_callback", methods=["POST"])
def twilio_calling_callback():
    """
    Twilio Voice Status Callback

    Receives a callback from Twilio when the call status changes. If the call is completed,
    it processes the response data and updates lead and IVR information in the database.

    ---
    tags:
      - Twilio
    summary: Handle Twilio Voice Status Callback
    description: >
      This endpoint is called by Twilio when a voice call status changes (typically to "completed").
      It logs the callback, updates the lead data in the database, and performs necessary logic
      to determine whether the lead is "Completed" or "Incomplete".


    parameters:
      - name: CallSid
        in: formData
        type: string
        required: false
        description: Unique Twilio call SID.
      - name: CallStatus
        in: formData
        type: string
        required: true
        description: Status of the call (e.g., completed, ringing, busy).
        example: completed
      - name: Caller
        in: formData
        type: string
        required: false
        description: Phone number of the caller.
        example: +11234567890
      - name: From
        in: formData
        type: string
        required: false
        description: The phone number that made the call.
      - name: To
        in: formData
        type: string
        required: false
        description: The phone number that received the call.
    responses:
      200:
        description: Callback processed successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Success
            data:
              type: object
              additionalProperties: true
            status:
              type: integer
              example: 200
    """
    data = request.form.to_dict()
    print(f"voice_status_callback {data}")
    add_redis_ttl_data(f"VSC_{data.get("CallSid")}_{uuid4().hex}", 336, data)
    get_twilio_status_call_back(data)
    return jsonify({"message": "Success", "data": data, "status": 200})


@twilio_bp.route("/response/incomplete", methods=["POST"])
def twilio_calling_response_incomplete():
    """
    Handle Incomplete IVR Response from Twilio

    Receives and stores partial IVR input data from Twilio. This data may be incomplete due to the caller hanging up or not completing the IVR process.

    ---
    tags:
      - Twilio
    summary: Handle Incomplete IVR Response
    description: >
      This endpoint is triggered by Twilio to save incomplete IVR call data, such as partial answers or
      abandoned calls. It stores the data temporarily and updates or creates lead response records accordingly.

    parameters:
      - name: mortgage_id
        in: formData
        type: string
        required: true
        description: Mortgage ID associated with the lead.
        example: 987654
      - name: ani
        in: formData
        type: string
        required: false
        description: Automatic Number Identification (caller phone number).
        example: +11234567890
      - name: coborrower
        in: formData
        type: string
        required: false
        description: Indicates presence of co-borrower (1 = Yes, 2 = No/Skip).
        example: 2
      - name: health
        in: formData
        type: string
        required: false
        description: Health status of the caller (1 = Good, 2 = Poor/Skip).
        example: 1
      - name: tobacco
        in: formData
        type: string
        required: false
        description: Tobacco use status (1 = Yes, 2 = No).
        example: 2
      - name: spouse
        in: formData
        type: string
        required: false
        description: Indicates if the caller has a spouse (1 = Yes, 2 = No/Skip).
        example: 1
    responses:
      200:
        description: Incomplete response processed successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
    """
    data = request.form.to_dict()
    print(data)
    add_redis_ttl_data(f"TRI_{data['sid']}_{uuid4().hex}", 336, data)
    twilio_call_response_incomplete(data)
    return jsonify({"message": "Success", "status": 200})


def extract_mortgage_id_from_text(text: str) -> Tuple[Optional[str], str]:
    client = OpenAI(api_key=Config_is.OPENAI_API_KEY)
    """
    Extract a 7-digit mortgage ID from noisy text using OpenAI with contextual validation.
    Return: (clean_digit_string or None, voice_response_message)
    """
    prompt = f"""
    You are a speech-to-text cleanup assistant. Your task is to extract a 7-digit mortgage ID from spoken or messy user input.

    Instructions:
    - Identify and convert number words to digits (e.g., 'seven' → 7, 'to' → 2).
    - Ignore non-numeric symbols (e.g., commas, periods, slashes).
    - If no digits can be confidently extracted, reply: "Sorry, I didn't catch any numbers."
    - If the digits extracted are not exactly 7, reply: "I heard the number {{number}}, but it's not 7 digits."
    - If exactly 7 digits are extracted, reply: "You said {{number}}. Is that correct?"
    Text: "{text}"
    Only respond with the appropriate message above.
    """
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        print("OpenAI raw response:", content)
        match = re.search(r'(?:number|said)\s+([0-9\s,]+)', content)
        if match:
            digit_str = match.group(1)
            digits_only = re.sub(r'[^0-9]', '', digit_str)
            print("Extracted digits:", digits_only)

            if not digits_only:
                return None, "Sorry, I didn't catch any numbers."
            elif len(digits_only) != 7:
                comma_separated = ", ".join(digits_only)
                return None, f"I heard the number {comma_separated} but it's not 7 digits."
            else:
                comma_separated = ", ".join(digits_only)
                return digits_only, f"You said {comma_separated}."
        else:
            return None, "Sorry, I didn't catch any numbers."
    except Exception as e:
        print("OpenAI extraction error:", e)
        return None, "Sorry, I'm having trouble processing your response. Please try again."
    