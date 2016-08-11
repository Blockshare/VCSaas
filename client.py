# Loading Developer Libraries
from two1.commands.config import Config
from two1.wallet import Wallet
from two1.bitrequests import BitTransferRequests

wallet = Wallet()
username = Config().username
requests = BitTransferRequests(wallet, username)

server_url = "http://localhost:5000/"

def get_funding():


    response = requests.get(url=server_url+'funding')
    
    print(response.text)

if __name__=='__main__':
    get_funding()    
