import requests
###This class is written purely for the purposes of being used by other users, as the developer of this project is lazy
### and steals the token strings straigh from Burp Suite (by the way it's great)
class AuthClass():
    def __init__(self):
        self.AccessToken = None
        self.IdToken = None
        self.RefreshToken = None
        self.__url = 'https://cognito-idp.us-east-1.amazonaws.com'
        self._code_sent = False
        self._headers = {'Content-Type': 'application/x-amz-json-1.1',
        'User-Agent': 'aws-sdk-android/2.22.5 Linux/4.0.9 Dalvik/2.1.0/0 en_US',
        # 'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
        'Aws-Sdk-Retry': '0/0',
        'Accept-Encoding': 'gzip, deflate',
        'Aws-Sdk-Invocation-Id': '0bb2e7f3-0936-4daf-ad25-96b83331b70d'}
    def SendSmsRequest(self,phone:str)->None:
        '''This function sends a user an sms with the code for authorization.'''
        body = {"AuthFlow":"CUSTOM_AUTH","AuthParameters":{"USERNAME":phone},"ClientMetadata":{},"ClientId":'7g1h82vpnjve0omfq1ssko18gl'}
        headers = self._headers
        headers['X-Amz-Target'] = 'AWSCognitoIdentityProviderService.InitiateAuth'
        x = requests.post(self.__url,headers=headers,json=body).json()
        if "__type"in x and x['__type']=='UserNotFoundException':
            raise Exception("No user with such phone found")
        else:
            self._username  = x['ChallengeParameters']['USERNAME']
            self._Session = x['Session']
            self._code_sent = True
    def AuthorizeWithCode(self,code_from_sms:str):
        '''This function is used to get an authorization session from a recieved sms code.'''
        body = {"ClientId":"7g1h82vpnjve0omfq1ssko18gl","ChallengeName":"CUSTOM_CHALLENGE","Session":self._Session,
                "ChallengeResponses":
                    {
                    "USERNAME":self._username,"ANSWER":code_from_sms
                    }
                }
        headers = self._headers
        headers['X-Amz-Target'] = 'AWSCognitoIdentityProviderService.RespondToAuthChallenge'
        x = requests.post(self.__url,headers = headers,json=body).json()
        if '__type' in x and x['__type']=='NotAuthorizedException':
            #I don't care that much about handling exceptions, as the user
            #should know what he is doing if he is using this code outside of this project.
            raise Exception("NotAuthorizedException")
        else:
            auth_res = x['AuthenticationResult']
            self.AccessToken = auth_res['AccessToken']
            self.IdToken = auth_res['IdToken']
            self.RefreshToken = auth_res['RefreshToken']


