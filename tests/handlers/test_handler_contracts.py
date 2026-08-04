
from testforge.handlers.primeFaces import PrimeFacesHandler
from testforge.handlers.react_mui import ReactMUIHandler


def test_primefaces_handler_satisfies_component_contract():
    handler = PrimeFacesHandler()
    assert handler.component_type == "primefaces"


def test_react_mui_handler_satisfies_component_contract():
    handler = ReactMUIHandler()
    assert handler.component_type == "react-mui"

