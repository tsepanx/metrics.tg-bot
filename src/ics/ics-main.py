import functools
import logging
import os

import fastapi
import uvicorn
from fastapi import (
    FastAPI,
    HTTPException,
)
from fastapi.responses import (
    FileResponse,
)

from src.ics.generate import (
    gen_ics_from_answers_db,
)

app = FastAPI()

HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "80"))


def raise_proper_http(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
            ) from e

        return result

    return wrapper


# pylint: disable=too-many-arguments
@app.get("/ics/{username}", response_class=FileResponse)
@raise_proper_http
async def get_feed(
    username: str,
):
    from src.user_data import (
        UserDBCache,
    )

    # TODO fetch only user-related, e.g. filter by UserId
    db_cache = UserDBCache()

    cal_str = gen_ics_from_answers_db(db_cache.answers)

    dirname = "gen_ics/"
    fname = f"{username}_events.ics"

    if not os.path.exists(dirname):
        os.mkdir(dirname)

    path = os.path.join(dirname, fname)

    f = open(path, "wb")
    f.write(cal_str)
    f.close()

    return FileResponse(path=path, media_type="text/calendar")


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )

    uvicorn.run(app=app, host=HTTP_HOST, port=HTTP_PORT)
