# import requests
# from config import Config_is
#
#
# def sms(mortgage_id: str, to: str, body: str) -> bool:
#     try:
#         response = requests.post(
#             f"https://hosting.plumvoice.com/ws/sms/queue.xml", headers={
#                 'Content-Type': 'application/x-www-form-urlencoded',
#                 'Authorization': f"Basic {Config_is.SMS_TOKEN}"},
#             data=f"sms_format=json&to={to}&from={Config_is.SMS_FROM}&body={body}&result_url={Config_is.BASE_URL}"
#                  f"v1/tele/sms_response/{mortgage_id}")
#         if response.status_code != 200:
#             return True
#     except Exception as e:
#         print(e)
#     return True
