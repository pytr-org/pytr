from typing import TypedDict, Optional, List
from typing import cast

class Name(TypedDict):
    first: str
    last: str

class Email(TypedDict):
    address: str
    verified: bool

class PostalAddress(TypedDict):
    street: str
    houseNo: str
    zip: str
    city: str
    country: str

class Birthplace(TypedDict):
    birthplace: str
    birthcountry: str

class TaxResidency(TypedDict):
    tin: str
    countryCode: str

class TaxExemptionOrder(TypedDict):
    minimum: int
    maximum: int
    current: int
    applied: int
    syncStatus: int
    validFrom: int
    validUntil: int

class CashAccount(TypedDict):
    iban: str
    bic: str
    bankName: str
    logoUrl: Optional[str]

class ReferenceAccount(TypedDict):
    iban: str
    bic: Optional[str]
    bankName: Optional[str]
    logoUrl: Optional[str]

class Experience(TypedDict):
    tradeCount: int
    level: str
    showsRiskWarning: bool

class InvestmentExperience(TypedDict):
    stock: Experience
    fund: Experience
    derivative: Experience
    crypto: Experience
    bond: Experience

class SupportDocuments(TypedDict):
    accountClosing: str
    imprint: str
    addressConfirmation: str

class TinFormat(TypedDict):
    placeholder: str
    keyboardLayout: str

class AccountDetails(TypedDict):
    phoneNumber: str
    jurisdiction: str
    name: Name
    email: Email
    duplicateTradingEmail: Optional[str]
    postalAddress: PostalAddress
    birthdate: str
    birthplace: Birthplace
    mainNationality: str
    additionalNationalities: List[str]
    mainTaxResidency: TaxResidency
    usTaxResidency: bool
    additionalTaxResidencies: List[TaxResidency]
    taxInformationSyncTimestamp: int
    taxExemptionOrder: TaxExemptionOrder
    registrationAccount: bool
    cashAccount: CashAccount
    referenceAccount: ReferenceAccount
    referenceAccountV2: Optional[str]
    referenceAccountList: List[ReferenceAccount]
    securitiesAccountNumber: str
    experience: InvestmentExperience
    referralDetails: Optional[str]
    supportDocuments: SupportDocuments
    tinFormat: TinFormat
    personId: str
    
    def from_dict(d):
        account_details: AccountDetails = cast(AccountDetails, d)
        return account_details
