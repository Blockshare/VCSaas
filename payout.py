# Copyright (c) 2010 Tom Pinckney
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:n

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
                     
from flask import Flask, request
from two1.wallet import Wallet
from two1.bitserv.flask import Payment

app = Flask(__name__)
wallet = Wallet()
payment = Payment(app, wallet)


class Funding(object):
    def __init__(self, name, price, shares):
        self.name = name
        self.price = price
        self.shares = shares
        return ("\n", name, "invests", self.price * self.shares, "at", self.price, "per share")

class PreferenceNonParticipating(object):
    def __init__(self, preferences):
        self._preferences = preferences
        return ("\twith", preferences, "x preferences")
        
    def liquidate(self, common_outstanding, capital):
        common_if_converted = self.convert_to_common()
        percent_ownership = float(common_if_converted) / common_outstanding
        total_invested = self.price * self.shares
        preferred_payout = min(total_invested * self._preferences, capital)
        common_payout = percent_ownership * capital
        if common_payout > preferred_payout:
            return (self.name, "opts to convert to", common_if_converted, "common shares")
            return 0.00, common_if_converted
        else:
            #print(self.name, "opts to take preferred payment of", preferred_payout)
            return preferred_payout, 0

class PreferenceParticipating(object):
    def __init__(self, preferences, cap):
        self._preferences = preferences
        self._preferences_cap = cap
        return ("\twith participating", preferences, "x preferences capped at ", cap, "x original per share price")

    def liquidate(self, common_outstanding, capital):
        common_if_converted = self.convert_to_common()
        percent_ownership = float(common_if_converted) / common_outstanding
        total_invested = self.price * self.shares
        preference_payout = min(total_invested * self._preferences, capital)
        if preference_payout < capital:
            preference_payout += (percent_ownership * (capital - preference_payout))
        preference_payout = min(preference_payout, self.price * self._preferences_cap * self.shares)            
        common_payout = percent_ownership * capital
        if preference_payout > common_payout:
            #print(self.name, "opts to take prefered payment of", preference_payout)
            return preference_payout, 0
        else:
            #print(self.name, "opts to convert to", common_if_converted, "common shares")
            return 0.00, common_if_converted

class AntiDilution(object):
    def convert_to_common(self):
        return self.shares * self.price / self._conversion_price

class AntiDilutionBroadWeighted(AntiDilution):
    def __init__(self, price):
        self._conversion_price = price
        return ("\twith broad-weighted anti-dilution provisions\n")
        
    def trigger_anti_dilution(self, company, new_round):
        if self.price > new_round.price:
            outstanding = company.common_outstanding_as_if_converted()
            price_ratio = new_round.price / self.price
            self._conversion_price = self._conversion_price * (outstanding + new_round.shares * price_ratio) / (outstanding + new_round.shares)
            return (self.name, "anti-dilution provisions cause conversion price to adjust to ", self._conversion_price)

class AntiDilutionFullRatchet(AntiDilution):
    def __init__(self, price):
        self._conversion_price = price
        return ("\twith full-ratchet anti-dilution provisions\n")

    def trigger_anti_dilution(self, company, new_round):
        if self.price > new_round.price:
            self._conversion_price = new_round.price
            return (self.name, "anti-dilution provisions cause conversion price to adjust to ", self._conversion_price)
            
class Company(object):
    def __init__(self, outstanding_options, founder_stock):
        self._capital = []
        self.outstanding_options = outstanding_options
        self.founder_stock = founder_stock

    def investment(self, new_round):
        for prior_round in self._capital:
            prior_round.trigger_anti_dilution(self, new_round)
        self._capital.append(new_round)

    def price_per_share(self, acquisition_price):
        #print("company acquired for", acquisition_price)
        #print(self.outstanding_options, "outstanding options and", self.founder_stock, "shares of founder stock")
        capital_remaining = float(acquisition_price)
        preferred_payments = 0
        common_to_be_paid = 0.00
        common_outstanding = self.common_outstanding_as_if_converted()
        for round in reversed(self._capital):
            preferred_payments, common = round.liquidate(common_outstanding, capital_remaining)
            capital_remaining -= preferred_payments
            common_to_be_paid += common
            print("after", round.name, "liquidates, capital remaining is $", capital_remaining, "\n")
            if capital_remaining <= 0.0:
                break
        common_to_be_paid += self.outstanding_options
        common_to_be_paid += self.founder_stock
        if capital_remaining > 0.0:
            common_price = capital_remaining / common_to_be_paid
            return common_price
        else:
            return 0.0

    def common_outstanding_as_if_converted(self):
        common = 0
        for round in self._capital:
            common += round.convert_to_common()
        common += self.outstanding_options
        common += self.founder_stock
        return common

# some example ways these classes can be combined to represent different types of terms
class SimpleFunding(Funding,PreferenceNonParticipating,AntiDilutionBroadWeighted):
    def __init__(self, name, price, shares, preferences):
        Funding.__init__(self, name, price, shares)
        PreferenceNonParticipating.__init__(self, preferences)
        AntiDilutionBroadWeighted.__init__(self, price)

class YouGotScrewedFunding(Funding,PreferenceParticipating,AntiDilutionFullRatchet):
    def __init__(self, name, price, shares, preferences, cap):
        Funding.__init__(self, name, price, shares)
        PreferenceParticipating.__init__(self, preferences, cap)
        AntiDilutionFullRatchet.__init__(self, price)

# An example of how to simulate the funding and acquisition of a
# company.  The company gives 2 million shares to founders, 2 million
# to the option pool and 2 million shares to the Series A investors
# for $2 million. The company goes on to raise $18 million more in a
# Series B and Series C.
#
# The company sells for $30 million.
#
# We find that the common stock is worth $1.68. So even though the
# founders owned 16% of the company, they would get only 11% of the
# proceeds due to the preferences.
#
# In particular, the Series A investor does well taking in $5.28 million
# or 18% of the sale due to their participating preferred.
#

founders_shares = 2000000
option_pool = 2000000
acquisition_price = 30000000
seriesA = YouGotScrewedFunding(name="Series A", price=1.00, shares=2000000, preferences=2, cap=3)
seriesB = SimpleFunding(name="Series B", price=2.00, shares=4000000, preferences=1)
seriesC = SimpleFunding(name="Series C", price=4.00, shares=2500000, preferences=1)
newco = Company(outstanding_options=option_pool, founder_stock=founders_shares)
newco.investment(seriesA)
newco.investment(seriesB)
newco.investment(seriesC)
common_price = newco.price_per_share(acquisition_price=acquisition_price)
number_common_shares = newco.common_outstanding_as_if_converted()
founders_own = round(float(founders_shares) / number_common_shares * 100)
founders_get = round(float(common_price * founders_shares) / acquisition_price * 100)

import json

@app.route('/funding')
@payment.required(1000)
def get_equity():
    
    
    data = {
        'founder_shares': founders_shares,
        'options_pool_size': option_pool,
        'acquisition_price': acquisition_price,
        'price_per_share': common_price,
        'number_of_shares': number_common_shares,
        'percentage_founders_own': founders_own,
        'percentage_founders_get': founders_get
    }        
  

    response = json.dumps(data, indent=2)
    return(response)
    


if __name__=='__main__':
    app.run(host='0.0.0.0', debug=True)
