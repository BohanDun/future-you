# AWS authentication and user profile setup

Future You uses Amazon Cognito for customer authentication and DynamoDB for
financial profiles. IAM Identity Center remains the developer login for AWS;
it is not the customer login system.

## 1. Create the Cognito user pool

In the Amazon Cognito console in `ap-southeast-2`:

1. Create a user pool named `future-you-users`.
2. Use **Email** as the sign-in identifier.
3. Enable self-service sign-up.
4. Require and automatically verify the `email` attribute.
5. Use verification codes sent by email.
6. Choose an appropriate password policy. The Cognito default is suitable for
   an MVP; production environments should review MFA and account-recovery rules.
7. Create a **public web/SPA app client** named `future-you-web`.
8. Do not generate an app client secret. A browser application cannot protect a
   client secret.
9. Enable SRP authentication and refresh-token authentication for the app
   client. The frontend uses Amplify Auth and Cognito's SRP flow.

Copy these public identifiers after creation:

- User pool ID, for example `ap-southeast-2_Example`
- App client ID

The custom React sign-in form uses Cognito APIs directly, so a Cognito managed
login domain is not required for this implementation.

## 2. Create the DynamoDB table

In DynamoDB in `ap-southeast-2`, create:

| Setting | Value |
| --- | --- |
| Table name | `future-you-users` |
| Partition key | `userId` |
| Partition key type | String |
| Billing mode | On-demand (`PAY_PER_REQUEST`) |
| Encryption | AWS owned key or a project-managed KMS key |

Each item also contains `customerId` with the same Cognito `sub` value because
the financial engine currently consumes the `CustomerProfile` model.

## 3. Configure local environment variables

Backend shell, before starting Uvicorn:

```bash
export AUTH_MODE=cognito
export DATA_SOURCE=dynamodb
export USER_PROFILE_TABLE_NAME=future-you-users
export COGNITO_USER_POOL_ID='your-user-pool-id'
export COGNITO_APP_CLIENT_ID='your-app-client-id'
export AWS_PROFILE=future-you
export AWS_REGION_NAME=ap-southeast-2
export AI_MODE=bedrock
export BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
export AGENT_PROPOSAL_SIGNING_KEY='a-private-random-value-of-at-least-32-characters'
export PYTHONPATH='../:.'
```

Frontend `.env.local`:

```env
VITE_API_URL=http://127.0.0.1:8000
VITE_AUTH_MODE=cognito
VITE_COGNITO_USER_POOL_ID=your-user-pool-id
VITE_COGNITO_USER_POOL_CLIENT_ID=your-app-client-id
```

User pool IDs and app client IDs are public configuration values. Never place
AWS access keys, session tokens, a Cognito client secret, or a Bedrock API key
in the frontend environment.

## 4. Grant backend permissions

For local development, the `future-you` SSO role needs these DynamoDB actions
on the `future-you-users` table:

- `dynamodb:GetItem`
- `dynamodb:PutItem`

It also needs the existing Bedrock model invocation permission.

For deployment, grant the same DynamoDB permissions to the Lambda execution
role. Do not give the browser direct DynamoDB permissions; all profile access
must go through the backend.

## 5. Protect API Gateway routes

The FastAPI application validates Cognito access tokens itself. For defence in
depth, also add an API Gateway JWT/Cognito authorizer:

- Issuer: `https://cognito-idp.ap-southeast-2.amazonaws.com/<user-pool-id>`
- Audience/app client: the `future-you-web` app client ID
- Token source: `Authorization` header

Keep `/health` public. Require authentication for `/me/profile`, `/simulate`,
and `/customer/{customer_id}`. The backend derives the real user ID from the
validated token and does not trust a browser-supplied customer ID.

## 6. Verify the flow

1. From the repository root, run `./start-aws.sh`. It will list any missing
   configuration instead of starting a partial AWS setup.
2. Start the frontend and create a new account.
3. Enter the email verification code.
4. Sign in and complete financial onboarding.
5. Confirm that DynamoDB contains an item whose `userId` is the Cognito user
   `sub`, not the email address.
6. Run a simulation and confirm that the backend returns the signed-in user's
   profile.
## 7. Secure Manage proposals

Manage mode signs every preview so the browser cannot alter an operation before it is
confirmed. Set `AGENT_PROPOSAL_SIGNING_KEY` to a private random value of at least 32
characters in the backend environment. Use the same value for every Lambda instance and
do not expose it through a `VITE_` variable or commit it to Git.

## 8. Return to the AWS-free Mock version

Stop the AWS processes and run this from the repository root:

```bash
./start-dev.sh
```

The Mock launcher explicitly selects Mock authentication, local JSON profile storage,
and deterministic AI responses. It does not call Cognito, DynamoDB, or Bedrock. Mock
changes persist in `backend/.local/mock-customers/` and remain separate from AWS data.
