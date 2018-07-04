"""KYC tests"""
import csl_reader


def basic_kyc(name, address, phone):
    """Basic kyc test"""
    csl_list_checker = csl_reader.CSLListChecker()
    name_score = csl_list_checker.score_name(name)
    address_score = csl_list_checker.score_address(address)
    phone_score = csl_list_checker.score_phone(phone)
    # if any of scorred parameters is greater than 0.95 then we can
    # assuredly say: user is scummer
    if any((score > .95 for score in (name_score, address_score, phone_score))):
        return 0
    average = sum((name_score, address_score, phone_score)) / 3
    return 0 if average > 0.85 else 1
