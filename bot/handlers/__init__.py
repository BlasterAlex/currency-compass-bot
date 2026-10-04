from aiogram import Router

from bot.handlers import currencies, rate, start

router = Router()
router.include_router(start.router)
router.include_router(currencies.router)
router.include_router(rate.router)
