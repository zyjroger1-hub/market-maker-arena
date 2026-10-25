# Deploy the interactive demo

The GitHub repository hosts source, reports and saved experiment artifacts.
The interactive application runs on a Python server; deployment is a separate step.

## Streamlit Community Cloud

1. Sign in at https://share.streamlit.io/ and connect the GitHub repository.
2. Create an app, select the repository and branch, and choose `app.py` as entrypoint.
3. In Advanced settings select Python 3.12, matching the tested major/minor version.
4. Deploy using the root `requirements.txt`, which loads the tested package lock.
5. Check visibility settings for the intended audience, and test in a signed-out window.
6. Add the verified app URL to the repository About section and README.

No secrets or exchange credentials are required. Do not upload a local virtual
environment. The cloud config intentionally has no fixed server address; local
launch scripts still bind to 127.0.0.1.

## Smoke test before sharing

- Play: advance a round, pause a quote side, replay, and finish a match.
- Research: inspect saved results and run a new 20-seed paired experiment.
- Confirm the distributions, inventory/drawdown plots and document images render.
- Check that synthetic-fill and terminal-marking explanations remain visible.
- Confirm downloads correspond to the applied configuration, not changed controls.

Community Cloud can hibernate inactive apps. Keep the GitHub report and figures
available as a stable fallback and wake the demo before an interview. Cloud
validation is not claimed until this deployment and smoke test actually finish.

Official references:
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app
