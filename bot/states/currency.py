from aiogram.fsm.state import State, StatesGroup


class CurrencyForm(StatesGroup):
    waiting_for_search = State()
