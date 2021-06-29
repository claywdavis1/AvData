from __future__ import print_function
import time
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from pprint import pprint

# Configure API key authorization: api-key
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = ''

# create an instance of the API class
api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
senderSmtp = sib_api_v3_sdk.SendSmtpEmailSender(name="test",email="claydavis1995@gmail.com")
sendTo = sib_api_v3_sdk.SendSmtpEmailTo(email="claywdavis1@gmail.com",name="Recipient Name")
arrTo = [sendTo] #Adding `to` in a list
send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(sender=senderSmtp,to=arrTo,html_content="This is a test",subject="This is a test subject") # SendSmtpEmail | Values to send a transactional email

try:
    # Send a transactional email
    api_response = api_instance.send_transac_email(send_smtp_email)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SMTPApi->send_transac_email: %s\n" % e)
