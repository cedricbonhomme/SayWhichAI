from ai_disclosure.github import GitHub


class Answering(GitHub):
    def __init__(self, kind: str):
        super().__init__("token")
        self.kind = kind

    def query(self, query: str, **variables: object) -> dict:
        return {"repository": {"owner": {"__typename": self.kind, "login": variables["owner"]}}}


def test_the_picture_of_an_organisation_is_a_logo():
    assert Answering("Organization").logo("MISP/MISP") == "MISP"


def test_the_portrait_of_a_person_is_not_a_logo():
    assert Answering("User").logo("ada/engine") == ""
