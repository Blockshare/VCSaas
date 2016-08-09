# Loading Developer Libraries
from two1.command.config import Config
from two1.wallet import Wallet
from two1.bitrequests import BitTransferRequests

wallet = Wallet()
username = Config().username
requests = BitTransferRequests(wallet, username)

server_url = "http://localhost:5000/"

def get_funding():

    shares = input("Enter the number of founder shares:\n")
    options = input("Enter the number of options in the pool:\n")
    price = input("Enter th acquisition price:\n")
    
    response = requests.get(url=server_url+"funding?shares={0}?pool={1}?price={2}".format(shares, options, price))
    return response.status_code


if __name__=='__main__':
    border = "------------------------------------------------"
    get_funding()    
