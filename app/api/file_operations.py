"""API Endpoints related to File uploader and download."""
import json
from flask import request, jsonify, Blueprint
from app.services.file_operations import (
    download_mortgage_file,
    uploaded_file_info_list,
    download_all_mailer_leads_except_mailed,
    csv_mailing_input_with_mortgage_id,
    report_download_processed_mailer_leads,
    upload_purchase_agreement,
    download_campaign_leads
)
from app.services.leads_operations import all_download_agent_mailing_leads
from app.api.auth import tokenAuth
from app.services.auth import admin_authorizer
from constants import (
    CSV_DOWNLOAD_MORTGAGE_FIELDS, 
    CSV_DOWNLOAD_IVR_COMPLETED_FIELDS
    )

files_bp = Blueprint("file_operations", __name__)


@files_bp.route('/upload/purchase_agreement/<id_>', methods=["POST"])
@tokenAuth.login_required
def uploading_purchase_agreement(id_):
    """
    ---
    summary: Upload a purchase agreement as a base64-encoded image
    description: |
      Uploads a base64-encoded image of a purchase agreement, converts it to a PDF, 
      and stores it in an Amazon S3 bucket. The request must include a Content-Type header 
      set to application/json and a valid Bearer token for authentication.
    operationId: uploadPurchaseAgreement
    tags:
      - Files
    parameters:
      - name: id_
        in: path
        required: true
        schema:
          type: string
          format: uuid
        description: Unique identifier for the purchase agreement (UUID format)
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - img
            properties:
              img:
                type: string
                description: Base64-encoded image data with data URI scheme (e.g., data:image/jpeg;base64,...)
                example: data:image/jpeg;base64,/9j/4AAQSkZJRgABAQE...
    responses:
      '200':
        description: Successful upload
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: Success
                status:
                  type: integer
                  example: 200
    security:
      - BearerAuth: []
    """
    upload_purchase_agreement(id_, request.json["img"])
    return jsonify({'message': 'Success', 'status': 200})


@files_bp.route("/upload/mailer-with-mortgage", methods=["POST"])
@tokenAuth.login_required
@admin_authorizer
def uploading_csv_file_with_mortgage_id():
    """
    Upload Mailing CSV with Mortgage IDs
    ---
    tags:
      - Files
    summary: Upload a CSV file containing mortgage leads with agent assignments
    security:
      - ApiKeyAuth: []
    consumes:
      - multipart/form-data
    parameters:
      - name: campaign
        in: formData
        type: string
        required: true
        description: Name of the campaign
      - name: csv_headers
        in: formData
        type: string
        required: true
        description: >
          A JSON string mapping standardized column names to actual CSV column headers.  
          Example: `{"AGENT_ID": "agent_id_column", "MORTGAGE_ID": "mortgage_id_column", "FULL_NAME": "name_column", ...}`
      - name: file
        in: formData
        type: file
        required: true
        description: CSV file containing mortgage data
      - name: source_id
        in: query
        type: integer
        required: true
        description: Source ID for this upload
      - name: category_id
        in: query
        type: integer
        required: true
        description: Category ID for this upload
    responses:
      200:
        description: File processed and records saved successfully
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                file_id:
                  type: string
                total_rows:
                  type: integer
                threads:
                  type: integer
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    print(request.form)
    print(request.files)
    data = csv_mailing_input_with_mortgage_id(
        request.form.get("campaign"),
        request.files["file"],
        request.args.get("source_id"),
        request.args.get("category_id"),
        json.loads(request.form.get("csv_headers")),
    )
    return jsonify({"data": data, "message": "success", "status": 200})


# @files_bp.route("/upload_digital_leads", methods=['POST'])
# @tokenAuth.login_required
# @admin_authorizer
# def uploading_csv_digital_leads():
#     file_is = request.files['file']
#     data = csv_iul_input_file(
#         request.form.get('campaign'), file_is, request.form.get('source_id'),
#         request.form.get('category'), json.loads(request.form['csv_headers']))
#     return jsonify({'data': data, 'message': 'success', 'status': 200})


@files_bp.route("/download/uploaded_mailer/<file_id>", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def downloading_mortgage(file_id):
    """
    Download Uploaded Mortgage Leads by File ID
    ---
    tags:
      - Files
    summary: Download mortgage leads uploaded under a specific file ID
    description: >
      Returns a list of mortgage leads associated with the uploaded file ID.
      The result is returned as JSON data with campaign-related fields.
    security:
      - ApiKeyAuth: []
    parameters:
      - name: file_id
        in: path
        type: string
        required: true
        description: Unique identifier of the uploaded file
      - name: campaign
        in: query
        type: string
        required: true
        description: Campaign name associated with this upload
    responses:
      200:
        description: List of mortgage leads retrieved successfully
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  mortgage_id:
                    type: integer
                    example: 71000001
                  full_name:
                    type: string
                    example: Alice Wonderland
                  agent_id:
                    type: integer
                    example: 1003
                  state:
                    type: string
                    example: CA
                  city:
                    type: string
                    example: ""
                  address:
                    type: string
                    example: street1
                  zip:
                    type: string
                    example: "90210"
                  lender_name:
                    type: string
                    example: ""
                  first_name:
                    type: string
                    example: Alice
                  last_name:
                    type: string
                    example: Wonderland
                  loan_type:
                    type: string
                    example: ""
                  loan_amount:
                    type: string
                    example: ""
                  loan_date:
                    type: string
                    example: "2024-01-01"
                  campaign:
                    type: string
                    example: dummyone
            headings:
              type: array
              items:
                type: string
              example: ["mortgage_id", "full_name", "agent_id", "state", "city", "address", "zip", "lender_name", "first_name", "last_name", "loan_type", "loan_amount", "loan_date", "campaign"]
            campaign:
              type: string
              example: June Campaign
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
      400:
        description: Bad request, invalid input parameters
      401:
        description: Unauthorized access
      403:
        description: Forbidden - admin access required
      404:
        description: File or campaign not found
    """
    response = download_mortgage_file(file_id, request.args["campaign"])
    return jsonify(
        {
            "data": response, 
            "headings": CSV_DOWNLOAD_MORTGAGE_FIELDS, 
            "campaign": request.args["campaign"], 
            "message": "Success", 
            "status": 200
            })


@files_bp.route("/<int:category_id>/paginated", methods=["GET"])
@tokenAuth.login_required
@admin_authorizer
def uploaded_file_info_listing_page(category_id):
    """
    Retrieves a paginated list of uploaded files for a given category.

    ---
    tags:
      - Files
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
        description: ID of the category to fetch uploaded files for.
      - name: page
        in: query
        type: integer
        required: false
        default: 1
        description: Page number for pagination.
      - name: per_page
        in: query
        type: integer
        required: false
        default: 10
        description: Number of results per page.
      - name: search
        in: query
        type: string
        required: false
        description: Search keyword to filter by campaign name.
    responses:
      200:
        description: A list of uploaded files.
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                description: Uploaded file details.
            pagination:
              type: object
              properties:
                total:
                  type: integer
                  description: Total number of results.
                current_page:
                  type: integer
                  description: Current page number.
                per_page:
                  type: integer
                  description: Number of items per page.
                length:
                  type: integer
                  description: Number of items returned in current page.
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
      204:
        description: No content found for the given filters.
      401:
        description: Authentication failed or missing token.
      403:
        description: User not authorized to access this resource.
    security:
      - ApiKeyAuth: []
    """
    result, pagination = uploaded_file_info_list(
        category_id,
        int(request.args.get("page", 1)),
        int(request.args.get("per_page", 10)),
        request.args.get("search"),
    )
    return jsonify(
        {
            "data": result,
            "pagination": pagination,
            "message": "Success",
            "status": 200,
        }
        )


# /download_all_completed
@files_bp.route("/download_all_except_mailer", methods=["GET"])
@tokenAuth.login_required
def downloading_completed_leads():
    """
    Download All Completed Leads Except Mailed
    ---
    tags:
      - Files
    summary: Download all IVR-completed leads excluding mailed leads
    description: >
      Retrieves a list of all completed mortgage leads 
      that have not been mailed yet, for a specific agent or group of agents.
    security:
      - ApiKeyAuth: []
    parameters:
      - name: agent_id
        in: query
        type: integer
        required: false
        description: Agent ID to filter leads by. Required if the user is an admin (role_id = 1).
    responses:
      200:
        description: List of completed leads retrieved successfully
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  mortgage_id:
                    type: integer
                    example: 71000001
                  full_name:
                    type: string
                    example: Alice Wonderland
                  city:
                    type: string
                    example: Los Angeles
                  address:
                    type: string
                    example: 123 Elm Street
                  state:
                    type: string
                    example: CA
                  zip:
                    type: string
                    example: "90210"
                  lender_name:
                    type: string
                    example: Chase Bank
                  first_name:
                    type: string
                    example: Alice
                  last_name:
                    type: string
                    example: Wonderland
                  loan_amount:
                    type: string
                    example: "$250,000"
                  loan_date:
                    type: string
                    example: "2024-06-01"
                  agent_id:
                    type: integer
                    example: 1003
                  campaign_name:
                    type: string
                    example: June Mortgage Campaign
                  lead_status:
                    type: string
                    example: 1
                  ivr_response:
                    type: string
                    example: Positive
                  call_in_time:
                    type: string
                    example: "2024-06-19 10:30:00"
                  completed:
                    type: boolean
                    example: true
            headings:
              type: array
              items:
                type: string
              example: ["mortgage_id", "full_name", "city", "address", "state", "zip", "lender_name", "first_name", "last_name", "loan_amount", "loan_date", "agent_id", "campaign_name", "lead_status", "ivr_response", "call_in_time", "completed"]
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
    """
    response = download_all_mailer_leads_except_mailed(request.args.get("agent_id"))
    return jsonify(
        {
            "data": response,
            "headings": CSV_DOWNLOAD_IVR_COMPLETED_FIELDS,
            "message": "Success",
            "status": 200,
        }
        )


@files_bp.route("/report/download_processed_leads", methods=["POST"])
@tokenAuth.login_required
@admin_authorizer
def downloading_processed_leads():
    """
    Download Processed Leads Report
    ---
    tags:
      - Files
    summary: Download a report of processed  leads within a date range
    description: >
      Returns a list of processed mortgage leads filtered by a date range and optional `completed` flag.
      If `page` is not provided, the API returns the total number of leads and pages for pagination.
    security:
      - ApiKeyAuth: []
    parameters:
      - name: page
        in: query
        type: integer
        required: false
        description: Page number for pagination. If omitted, only metadata (total, pages) is returned.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - start_date
              - end_date
            properties:
              start_date:
                type: string
                example: "06-01-2024"
                description: Start date in MM-DD-YYYY format
              end_date:
                type: string
                example: "06-10-2024"
                description: End date in MM-DD-YYYY format
              completed:
                type: boolean
                example: true
                description: (Optional) Filter by completed status
    responses:
      200:
        description: Successfully retrieved processed leads or pagination metadata
        schema:
          type: object
          properties:
            data:
              oneOf:
                - type: array
                  items:
                    type: object
                    properties:
                      mortgage_id:
                        type: integer
                        example: 71000001
                      full_name:
                        type: string
                        example: Alice Wonderland
                      state:
                        type: string
                        example: CA
                      city:
                        type: string
                        example: Los Angeles
                      address:
                        type: string
                        example: 123 Elm St
                      zip:
                        type: string
                        example: 90210
                      lender_name:
                        type: string
                        example: Wells Fargo
                      loan_amount:
                        type: string
                        example: "$250,000"
                      loan_date:
                        type: string
                        example: "2024-06-05"
                      agent_id:
                        type: integer
                        example: 1012
                      agent_name:
                        type: string
                        example: John Doe
                      campaign_name:
                        type: string
                        example: Summer 2024 Campaign
                      lead_status:
                        type: string
                        example: 1
                      ivr_response:
                        type: string
                        example: Positive
                      completed:
                        type: boolean
                        example: true
                      call_in_time:
                        type: string
                        example: "2024-06-07 15:30:00"
                - type: object
                  properties:
                    total:
                      type: integer
                      example: 2500
                    pages:
                      type: integer
                      example: 3
            message:
              type: string
              example: Success
            status:
              type: integer
              example: 200
    """
    response = report_download_processed_mailer_leads(
        request.json, request.args.get("page")
    )
    return jsonify({"data": response, "message": "Success", "status": 200})


@files_bp.route("/leads_details/download/<int:category>", methods=["POST"])
@tokenAuth.login_required
def getting_leads_for_download(category):
    
    """
    Download Leads from Agent Profile (completed/incompleted/Mailer)
    ---
    tags:
      - Leads
    summary: Download leads (completed/incomplete/mailed) from an agent profile
    description: >
      Downloads leads for a given category (e.g., completed, incomplete, mailed) from the agent profile. 
      The query filters in the request body determine the type and quantity of leads returned.
    security:
      - ApiKeyAuth: []
    parameters:
      - name: category
        in: path
        type: integer
        required: true
        description: Category of leads to download (1 = Mailing leads)
      - name: total
        in: query
        type: integer
        required: false
        default: 10
        description: Total number of leads to fetch (used for pagination/threading)
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              completed:
                type: boolean
                example: true
                description: Filter to retrieve only completed leads
              is_mailed:
                type: boolean
                example: false
                description: Filter to retrieve only unmailed leads
              agent_id:
                type: integer
                example: 1012
              campaign_name:
                type: string
                example: "Summer Campaign"
              state:
                type: string
                example: "CA"
              city:
                type: string
                example: "Los Angeles"
              loan_amount_min:
                type: number
                example: 100000
              loan_amount_max:
                type: number
                example: 500000
              start_date:
                type: string
                example: "06-01-2024"
                description: Filter leads from this date (MM-DD-YYYY)
              end_date:
                type: string
                example: "06-30-2024"
                description: Filter leads up to this date (MM-DD-YYYY)
    responses:
      200:
        description: Leads data retrieved successfully
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  mortgage_id:
                    type: integer
                    example: 71000001
                  source_id:
                    type: string
                    example: "SRC123"
                  full_name:
                    type: string
                    example: Alice Wonderland
                  state:
                    type: string
                    example: CA
                  city:
                    type: string
                    example: Los Angeles
                  address:
                    type: string
                    example: "123 Elm Street"
                  zip:
                    type: string
                    example: "90210"
                  first_name:
                    type: string
                    example: Alice
                  last_name:
                    type: string
                    example: Wonderland
                  lender_name:
                    type: string
                    example: Chase Bank
                  loan_amount:
                    type: string
                    example: "$250,000"
                  loan_date:
                    type: string
                    example: "2024-06-10"
                  agent_id:
                    type: integer
                    example: 1012
                  campaign_name:
                    type: string
                    example: June Campaign
                  lead_status:
                    type: string
                    example: Completed
                  ivr_response:
                    type: string
                    example: "Positive"
                  completed:
                    type: boolean
                    example: true
                  call_in_date_time:
                    type: string
                    example: "2024-06-15 14:30:00"
            message:
              type: string
              example: success
            status:
              type: integer
              example: 200
    """
    if category == 1:
        result = all_download_agent_mailing_leads(
            request.json, int(request.args.get("total", 10))
        )
        # elif category == 2:
        #     result = all_download_agent_digital_leads(int(request.args.get('agent_id')), int(request.args.get('source_id')), request.json, int(request.args.get('total', 10)), request.args.get('suppressed'))
    return jsonify({"data": result, "message": "success", "status": 200})

@files_bp.route("/download/campaign_leads", methods=["GET"])
@tokenAuth.login_required
def download_leads_by_campaign():
        """
        Download Campaign Leads
        ---
        tags:
          - Leads
        summary: Download all leads for a specific campaign
        description: |
          Returns a JSON payload containing every mortgage lead that belongs to the
          **campaign** supplied in the path.  
          * If the authenticated user is not an admin (`g.user["role_id"] != 1`)
            the results are automatically filtered to the user’s
            `mailing_agent_ids`.  
          * If the campaign has **no** matching leads, the API replies with
            **204 No Content**.  
          * Internally the data are paginated and processed in parallel, but the
            caller receives a single JSON array.

        parameters:
          - name: campaign
            in: query
            required: true
            description: Name (or slug) of the campaign whose leads you want to download
            type: string
            example: july‑2025‑refi

        produces:
          - application/json

        responses:
          200:
            description: Successful retrieval of campaign leads
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    type: object
                    properties:
                      mortgage_id:
                        type: string
                        example: "2004664"
                      full_name:
                        type: string
                        example: "John Doe"
                      agent_id:
                        type: integer
                        example: 42
                      state:
                        type: string
                        example: "CA"
                      city:
                        type: string
                        example: "Los Angeles"
                      address:
                        type: string
                        example: "123 Main St"
                      zip:
                        type: string
                        example: "90001"
                      lender_name:
                        type: string
                        example: "Wells Fargo"
                      first_name:
                        type: string
                        example: "John"
                      last_name:
                        type: string
                        example: "Doe"
                      loan_type:
                        type: string
                        example: "Refi"
                      loan_amount:
                        type: number
                        format: float
                        example: 350000
                      loan_date:
                        type: string
                        format: date
                        example: "2025‑06‑15"
                headings:
                  type: array
                  items:
                    type: string
                  description: Column headings (re‑used from `CSV_DOWNLOAD_MORTGAGE_FIELDS`)
                  example: ["Identifier", "Lead Full Name", "City", "State", "..."]
                campaign:
                  type: string
                  example: "july‑2025‑refi"
                message:
                  type: string
                  example: "Success"
                status:
                  type: integer
                  example: 200
        """
        leads = download_campaign_leads(request.args.get("campaign"))
        return jsonify({
            "data": leads,
            "headings": CSV_DOWNLOAD_MORTGAGE_FIELDS,  
            "campaign": request.args.get("campaign"),
            "message": "Success",
            "status": 200
        })
   
