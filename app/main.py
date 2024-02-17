from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from routers import (
    gpt_router,
    user_router,
    thread_router,
    auth_router,
    assistant_router,
)
from db.database import engine
from db import models
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # TODO: Remove this in production
# models.Base.metadata.drop_all(bind=engine)

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app.include_router(assistant_router.router)
app.include_router(auth_router.router)
app.include_router(gpt_router.router)
app.include_router(thread_router.router)
app.include_router(user_router.router)


@app.get("/privacy", response_class=HTMLResponse)
async def privacy():
    # return html
    return """<div>
    <h2>OpenGPTs</h2>

    <h1>Privacy Policy</h1>
    <p>Last updated: October 6, 2023</p>
    <p>
        At OpenGPTs, we respect your privacy and are committed to protecting
        it. This Privacy Policy explains how we collect, use, disclose, and
        safeguard your information when you visit our website.
    </p>
    <h2>Information We Collect</h2>
    <p>
        We may collect information about you in a variety of ways. The
        information we may collect on the website includes:
    </p>
    <ul>
        <li>
            Personal Data: While using our service, we may ask you to provide us
            with certain personally identifiable information.
        </li>
        <li>
            Usage Data: We may also collect information on how the service is
            accessed and used.
        </li>
    </ul>
    <h2>Use of Your Information</h2>
    <p>
        We use the information we collect in various ways, including to:
    </p>
    <ul>
        <li>Provide, operate, and maintain our website.</li>
        <li>Improve, personalize, and expand our website.</li>
        <li>Understand and analyze how you use our website.</li>
    </ul>
    <h2>Disclosure of Your Information</h2>
    <p>
        We do not sell, trade, or otherwise transfer to outside parties your
        personally identifiable information.
    </p>
    <h2>Third-Party Services</h2>
    <p>
        We contain links to third-party websites and applications of interest.
        Once you have used these links to leave our site, any information you
        provide is governed by the privacy policy of the operator of the site
        you are visiting.
    </p>
    <h2>Contact Us</h2>
    <p>
        If you have questions or comments about this Privacy Policy, please
        contact me at: 1sebastian1sosa1@gmail.com
    </p>
</div>"""  # noqa
