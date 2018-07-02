"""KYC tests"""
import csl_reader


def basic_kyc(name, address, phone):
    """Basic kyc test"""
    csl_list_checker = csl_reader.CSLListChecker()
    name_score = csl_list_checker.score_name(name)
    address_score = csl_list_checker.score_address(address)
    phone_score = csl_list_checker.score_phone(phone)
    average = sum(name_score, address_score, phone_score) / 3
    return 0 if average > 0.85 else 1

