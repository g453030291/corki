from corki.settings import BASE_DIR

TMP_PATH = str(BASE_DIR) + "/corki/tmp/"

SCORE_TYPE_LIST = [
    "project_exp_score",
    "communication_score",
    "professional_score",
    "logic_score",
    "teamwork_score",
    "learning_score"]

USER_CACHE_SECONDS = 30 * 24 * 60 * 60

NEW_USER_FREE_SECONDS = 999