USER_ROLE = {1: 'Admin', 2: 'Agent'}
SENDGRID_EVENTS = {
    1: 'User Invitation', 
    2: 'Reset Password Requets',
    3: 'Account reactivation/deactivation',
    4: 'New User Intent',
    5: 'Purchase Email',
    6: 'Admin Purchase Email Alert',
    7: 'User Intent Rejection',
    8: 'Stripe Subscription Webhook',
    9: 'New IVR lead alert',
    10: 'Suppression Requested',
    11: 'Marketplace Purchase Email',
    12: 'Failed Payment'
    }
LEAD_CATEGORY = {
    1: {
        "name": "Mailing Campaign",
        "sources": {
            1: {"name": "NEW MTG"}
        }
    },
    # 2: {
    #     "name": "Digital Leads",
    #     "sources": {
    #         4: {"name": "Health Insurance"}
    #     }
    # }
}

CSV_DOWNLOAD_MORTGAGE_FIELDS = ["Identifier", "Lead Full Name", "Client Address", "City", "State", "Zip", "Lender", "Loan Amount", "Loan Date", " Agent ID", "Call In Date", "Lead Phone Number", "Borrower Age", "Borrower Medical Issues", "Borrower Tobacco Use,Co-Borrower?", "Borrower Phone", "First Name", "Last Name", "Lead Status"]
CSV_DOWNLOAD_IVR_COMPLETED_FIELDS = ["Identifier", "Lead Full Name", "Client Address", "City", "State", "Zip", "Lender", "Loan Amount", "Loan Date", "Agent ID", "Call In Date", "Lead Phone Number", "Borrower Age", "Borrower Medical Issues", "Borrower Tobacco Use,Co-Borrower?", "Borrower Phone", "First Name", "Last Name", "Lead Status"]
IVR_COMPLETED_CSV_DOWNLOAD_FIELDS = []
PRICING_DETAIL_MONTH = {
    0: {'name': "Fresh leads"},
    1: {'name': "1+ month (1-2 months)",  'start_day': 30, 'end_day': 60},
    2: {'name': "2+ month (2-3 months)", 'start_day': 60, 'end_day': 90},
    3: {'name': "3+ month (3-6 months)", 'start_day': 90, 'end_day': 180}, 
    6: {'name': "6+ month (6-9 months)", 'start_day': 180, 'end_day': 270}, 
    9 : {'name': "9+ month (9-24 months)", 'start_day': 270, 'end_day': 730}
    }

DISABLED_STATES = []
TRANSACTION_RESPONSE = {2: "Declined", 3: "Error", 4: "Held for Review"}
FLAGGED_IVR_RESULT = {'0': 'NO', '1': 'YES'}
# LEAD_STATUS = {1: 'NEW', 2: 'FIRST CALL', 3: 'SECOND CALL', 4: 'THIRD CALL', 5: 'VOICEMAIL', 6: 'TEXT',
#                7: 'DOORKNOCK', 8: 'APPOINTMENT', 9: 'SOLD', 10: 'NOT INTERESTED', 11: 'SIT / DECLINED',
#                12: 'SIT / FOLLOW UP', 13: 'NO CONTACT', 14: 'DNC REQUEST', 15: 'ARCHIVE', 16: 'NO SHOW',
#                17: 'SIT / NO SALE', 18: 'SPANISH', 19: 'SUPPRESSED', 20: 'Suppression Denied'}
LEAD_STATUS = {1: 'NEW', 2: 'FIRST CALL', 3: 'SECOND CALL', 4: 'THIRD CALL', 5: 'TEXT',
               6: 'APPOINTMENT', 7: 'SOLD', 8: 'NOT INTERESTED', 9: 'SIT / NO SALE', 
               10:  'NO SHOW',  11: 'DNC', 12: 'SUPPRESSED', 13: 'Suppression Denied'}

# EXCLUDED_STATUS_FILTER_FROM_SALE = [7, 12, 13]  # sold & suppress LIST discard it from sales
EXCLUDED_STATUS_FILTER_FROM_SALE = [7, 8, 11] # now suppressed case is not required so only adding sold leads here
EXCLUDED_STATUS_OCCUR_TWO_TIME = [11, 8]
STRIPE_COMMISSION_FEE = .03  # 3% commmision
USA_STATES = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    # "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY"
}
COMPANY_INVOICE_ADDRESS = {
        "name": "KovaLifeLeads Insurance Company",
        "address": "15075 Southwest 49th Lane, Apt E, Miami, Florida, 33185",
        "phone": "+1 123-456-7890",
        "email": "admin@kovalifeleads.com"
    }
OPENAI_MODEL = "gpt-4"