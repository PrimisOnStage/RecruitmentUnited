

# Getting Started With The API

Our open API makes it easy to integrate other applications into BambooHR. Use this guide to get started sharing your data across systems.

## Easy to access. Easy to modify.

The BambooHR API is a RESTful Internet protocol built around making semantically meaningful HTTPS requests to access or modify a resource (usually done by an employee). The API can be used to manipulate employee data and to generate reports in several formats.

## What will you need to get started?

* A software developer to write code
* An HTTP client:
  * This library may help you get started: [https://documentation.bamboohr.com/docs/language-bindings](https://documentation.bamboohr.com/docs/language-bindings)
  * [Postman](https://www.getpostman.com/).

## Authentication

* Create a free account at BambooHR's [developer portal](https://developers.bamboohr.com/login)
* Create an application in the developer portal to get a client ID and secret
* Create a test BambooHR account to develop against
* Implement an OAuth flow in your application, following the instruction below

**Note:** In all examples, replace `{companyDomain}` with the text that appears before `.bamboohr.com` in your company’s BambooHR URL. For example, if you log in at `https://mycompany.bamboohr.com`, your `companyDomain` is `mycompany`.

### OAuth flow

**Note:** The **Redirect URI** is the URL you registered when creating your app in the BambooHR Developer Portal. During the OAuth flow, BambooHR redirects users to this address along with a temporary authorization code. Make sure the Redirect URI you use in your requests exactly matches the one you registered — even small differences (such as an extra slash or capitalization change) can cause authentication errors.

Use this information to generate a token via a browser or curl:

```
https://{companyDomain}.bamboohr.com/authorize.php?request=authorize&state=new&response_type=code&scope=[multiple scopes separated by plus +]&client_id=<your App's client ID>&redirect_uri=<your App's Redirect URI as registered in the Developer Portal>
```

Your browser will redirect to the URI specified in `redirect_uri`, with additional information `&code=` followed by a temporary code.

Use this information to generate a token using the following call:

```
https://{companyDomain}.bamboohr.com/token.php?request=token
Body
{
   "client_secret": "<your App's client secret>",
   "client_id": "<your App's client ID>",
   "code": "<temporary code>",
   "grant_type": "authorization_code",
   "redirect_uri": "<your App's Redirect URI as registered in the Developer Portal>"
}
```

The API will return following response:

```
{
    "access_token": "<temporary access token>",
    "expires_in": 3600,
    "token_type": "Bearer",
    "scope": "<scopes separated by space>",
    "refresh_token": "<temporary refresh token>",
    "id_token": "<unique ID>",
    "companyDomain": "<your company domain>"
}
```

You can now use the `<Temporary access token>` in subsequent calls. In Postman, select 'Bearer Token' and enter the `<Temporary access token>` in the Token field.

NOTE: the refresh\_token field will only be returned if you provided the `offline_access` scope in your original request to authorize.php. If you want to refresh your access token then you can use the refresh token in a call that looks like this:

```
https://{companyDomain}.bamboohr.com/token.php?request=token
Body
{
   "client_secret": "<your App's client secret>",
   "client_id": "<your App's client ID>",
   "refresh_token": "<your temporary refresh token>",
   "grant_type": "refresh_token",
   "redirect_uri": "<your App's Redirect URI as registered in the Developer Portal>"
}
```

OAuth is available in many APIs and requires configuring an application through the Developer Portal. Companies and developers can work with the BambooHR Marketplace team for support setting this up. You will need a BambooHR Application that includes Client ID and Client secret.

**If you are a customer or are building an integration for a single BambooHR customer:**

* An account with BambooHR
* The company domain used to access your account (If you access BambooHR at `https://mycompany.bamboohr.com`, then the company domain is `mycompany`)
* An API key

Each API request sent from a third-party application to the BambooHR website will be authenticated and permissioned as if a real user were using the software. The permissions of the user associated with the API request will determine which fields and employees each API request is allowed to view and/or edit.

To generate an API key, users should log in and click their name in the lower left-hand corner of any page to get to the user context menu. If they have sufficient permissions, there will be an "API Keys" option in that menu to go to the page.

Each user may have one or more secret API keys that identify that user to the API. The API secret key is a 160-bit number expressed in hexadecimal form. This is an astronomically large number of unique keys, which means that guessing an API key is nearly impossible.

At the HTTP level, the API key is sent over HTTP Basic Authentication. Use the secret key as the username and any random string for the password.

To use curl to make an API request try:

```curl
curl -i -u "{API Key}:x" "https://{companyDomain}.bamboohr.com/api/v1/employees/directory"
```

To use Postman to make an API request using basic authentication, look at [this documentation](https://learning.postman.com/docs/sending-requests/authorization/authorization-types/#basic-auth).

For more information about HTTP Basic Authentication, see [this helpful wikipedia article](https://en.wikipedia.org/wiki/Basic_access_authentication#Client_side).

If an unknown API key is used repeatedly, the API will disable access for a period of time. Users will still be able to log in to the BambooHR website during this time. When the API is disabled, it will send back an HTTP 403 Forbidden response to any requests it receives.

For more information about HTTP Basic Authentication, see [Basic Authentication](https://en.wikipedia.org/wiki/Basic_access_authentication#Client_side) and for OAuth see [OAuth](https://en.wikipedia.org/wiki/OAuth).