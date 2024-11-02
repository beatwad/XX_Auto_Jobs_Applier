import pytest
from unittest.mock import Mock
from src.bot_facade import BotState, BotFacade

@pytest.fixture
def bot_state():
    return BotState()

@pytest.fixture
def bot_facade():
    login_component = Mock()
    apply_component = Mock()
    return BotFacade(login_component, apply_component)


# Tests for BotState
def test_initial_state(bot_state):
    # Ensure the initial state flags are all False
    assert not bot_state.parameters_set
    assert not bot_state.logged_in
    assert not bot_state.search_parameters_set
    assert not bot_state.resume_set
    assert not bot_state.gpt_answerer_set

def test_reset(bot_state):
    # Set some state flags and then reset them
    bot_state.parameters_set = True
    bot_state.logged_in = True
    bot_state.reset()
    
    # Ensure reset worked as expected
    assert not bot_state.parameters_set
    assert not bot_state.logged_in
    assert not bot_state.search_parameters_set
    assert not bot_state.resume_set
    assert not bot_state.gpt_answerer_set

def test_validate_state_success(bot_state):
    # Set all required state flags and validate them
    bot_state.parameters_set = True
    bot_state.logged_in = True
    bot_state.search_parameters_set = True
    bot_state.resume_set = True
    bot_state.gpt_answerer_set = True
    bot_state.validate_state(['parameters_set', 'logged_in', 'search_parameters_set', 'resume_set', 'gpt_answerer_set'])

def test_validate_state_failure(bot_state):
    # Check that validate_state raises ValueError if a flag is missing
    with pytest.raises(ValueError, match="Флаг Parameters set должен быть установлен"):
        bot_state.validate_state(['parameters_set'])


# Tests for BotFacade
def test_set_parameters(bot_facade):
    parameters = {"key": "value"}
    
    # Mock methods for dependencies
    bot_facade.login_component.set_parameters = Mock()
    bot_facade.apply_component.set_parameters = Mock()
    
    # Set parameters and validate changes
    bot_facade.set_parameters(parameters)
    assert bot_facade.parameters == parameters
    assert bot_facade.state.parameters_set
    bot_facade.login_component.set_parameters.assert_called_once_with(parameters)
    bot_facade.apply_component.set_parameters.assert_called_once_with(parameters)

def test_start_login(bot_facade):
    # Set required state flags
    bot_facade.state.resume_set = True
    bot_facade.state.gpt_answerer_set = True
    bot_facade.login_component.start = Mock()
    
    # Start login and validate changes
    bot_facade.start_login()
    assert bot_facade.state.logged_in
    bot_facade.login_component.start.assert_called_once()

def test_set_search_parameters(bot_facade):
    # Set search parameters and validate state change
    bot_facade.apply_component.set_advanced_search_params = Mock()
    bot_facade.set_search_parameters()
    assert bot_facade.state.search_parameters_set
    bot_facade.apply_component.set_advanced_search_params.assert_called_once()

def test_set_resume(bot_facade):
    # Set resume profile and resume, then validate changes
    resume = {"resume": "example"}
    bot_facade.set_resume(resume)
    assert bot_facade.resume == resume
    assert bot_facade.state.resume_set

def test_set_gpt_answerer(bot_facade):
    # Mock dependencies and set required state
    gpt_answerer_component = Mock()
    bot_facade.resume = {"resume": "example"}
    bot_facade.state.resume_set = True
    
    # Set GPT answerer and validate state change
    bot_facade.set_gpt_answerer(gpt_answerer_component)
    assert bot_facade.state.gpt_answerer_set
    gpt_answerer_component.set_resume.assert_called_once_with(bot_facade.resume)

def test_start_apply(bot_facade):
    # Set all required flags for starting the apply process
    bot_facade.state.logged_in = True
    bot_facade.state.parameters_set = True
    bot_facade.state.search_parameters_set = True
    bot_facade.apply_component.start_applying = Mock()
    
    # Start applying and verify that process starts as expected
    bot_facade.start_apply()
    bot_facade.apply_component.start_applying.assert_called_once()


# Negative tests for private helper methods
def test_validate_non_empty(bot_facade):
    # Ensure _validate_non_empty raises ValueError if empty
    with pytest.raises(ValueError, match="Parameters cannot be empty."):
        bot_facade._validate_non_empty(None, "Parameters")

def test_ensure_resume_set(bot_facade):
    # Ensure _ensure_resume_set raises ValueError if resume is not set
    with pytest.raises(ValueError, match="Необходимо задать резюме для корректной работы."):
        bot_facade._ensure_resume_set()
