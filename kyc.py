"""KYC tests"""
import csl_reader


def basic_kyc(name):
    """Basic kyc test"""
    csl_list_checker = csl_reader.CSLListChecker()
    name_score = csl_list_checker.score_name(name)
    return 0 if name_score > 0.85 else 1
