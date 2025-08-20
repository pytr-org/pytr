import asyncio

from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK  # modificado

from pytr.account import login
from pytr.api import TradeRepublicApi


async def subscribe_price(tr_api: TradeRepublicApi, isin: str, exchange="LSX"):
    # Inicia la suscripción al precio mediante ticker
    await tr_api.ticker(isin, exchange)
    print(f"Subscribed to ticker for {isin} on {exchange}.")

    # Loop para recibir actualizaciones
    while True:
        subscription_id, subscription, response = await tr_api.recv()
        if subscription.get("type") == "ticker":
            price = response.get("last", {}).get("price")
            print(f"Updated price for {isin}: {price}")


async def subscribe_price_command(args):
    # Se usa login para obtener una instancia autenticada de TradeRepublicApi
    tr_api = await asyncio.to_thread(
        login,
        phone_no=args.phone_no,
        pin=args.pin,
        web=not args.applogin,
        store_credentials=args.store_credentials,
    )
    exchange = getattr(args, "exchange", "LSX")
    while True:
        try:
            await subscribe_price(tr_api, args.isin, exchange)
        except (ConnectionClosedError, ConnectionClosedOK):
            print("Connection closed, reconnecting...")
            await asyncio.sleep(1)
            continue
        except ValueError as e:
            if "validate connection token failed" in str(e):
                print("Token validation failed, re-authenticating...")
                tr_api = await asyncio.to_thread(
                    login,
                    phone_no=args.phone_no,
                    pin=args.pin,
                    web=not args.applogin,
                    store_credentials=args.store_credentials,
                )
                await asyncio.sleep(1)
                continue
            else:
                raise
        else:
            break


# Función para ejecutar la suscripción desde el CLI
def run_subscribe_price_command(args):
    asyncio.run(subscribe_price_command(args))
