# Why server ?

The garmin watch as well as the Android application connects to the server to have a common database, the server is mandatory for synchronization for the Garmin watch and not having the money to pay for a server for X people with X data for now you have to start the server yourself.

- [Why server ?](#why-server-)
  - [Server Setup](#server-setup)
    - [Heroku Installation](#heroku-installation)
      - [Automatic Installation](#automatic-installation)
      - [Manual installation](#manual-installation)
        - [1. Create an account or log in Heroku](#1-create-an-account-or-log-in-heroku)
        - [2. Create a new app](#2-create-a-new-app)
        - [3. Add add-ons Heroku Postgres](#3-add-add-ons-heroku-postgres)
        - [4. Deploy the code to Heroku](#4-deploy-the-code-to-heroku)
        - [5. Configuration](#5-configuration)
          - [To use search (optional)](#to-use-search-optional)
        - [6. Your application is now operational](#6-your-application-is-now-operational)
      - [Optional](#optional)
    - [Azure Setup](#azure-setup)
      - [Create a Resource Group](#create-a-resource-group)
      - [Create Postgres DB](#create-postgres-db)
      - [Use `psql` or Azure Data Studio or `pgadmin` to create a more restricted database user](#use-psql-or-azure-data-studio-or-pgadmin-to-create-a-more-restricted-database-user)
      - [Create an App Service](#create-an-app-service)
      - [Create Web App](#create-web-app)
      - [Deploy the code in this repo to the Web App](#deploy-the-code-in-this-repo-to-the-web-app)
      - [Set some environment variables to configure the webapp](#set-some-environment-variables-to-configure-the-webapp)
      - [Setup Automatic CI/CD (Optional)](#setup-automatic-cicd-optional)
  - [Create account](#create-account)
    - [Heroku](#heroku)
    - [Azure](#azure)
  - [Using App](#using-app)
    - [Web](#web)
    - [Android](#android)
    - [iOS](#ios)
    - [Garmin Connect](#garmin-connect)
  - [Question ?](#question-)

## Server Setup

### Heroku Installation

#### Automatic Installation

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

#### Manual installation

##### 1. Create an account or log in [Heroku](https://id.heroku.com/login)

##### 2. Create a new app

##### 3. Add add-ons [Heroku Postgres](https://elements.heroku.com/addons/heroku-postgresql)

The free version allows you to have 10,000 rows which is enough from my point of view for the majority of users.

##### 4. Deploy the code to Heroku

Perhaps the easiest is to use connect GitHub

##### 5. Configuration

You can define the numbers of users that your application can receive.
This allows you to limit the creation of accounts and suddenly the number of use of your database.

By default on free version Heroku you have access to 10,000 rows

Set ENV vars the NUMBER_MAX_USER

###### To use search (optional)

1. Get a [Podcast Index API token](https://api.podcastindex.org/)
2. Set ENV vars PODCASTING_INDEX_KEY and PODCASTING_INDEX_SECRET

##### 6. Your application is now operational

#### Optional

There is a cron to search for new episodes automatically.

The final step is to scale up the clock process. This is a singleton process, meaning you’ll never need to scale up more than 1 of these processes. If you run two, the work will be duplicated. [Visit the documentation](https://devcenter.heroku.com/articles/clock-processes-python)

```sh
heroku ps:scale clock=1
```

### Azure Setup

Assumes the use of `az` CLI.

#### Create a Resource Group

```sh
az group create mypodcasts --location eastus
```

#### Create Postgres DB

```sh
az postgres flexible-server create --location eastus --resource-group mypodcasts \
    --name mypgserver \
    --sku-name Standard_B1ms --tier Burstable \
    --admin-user mypgadmin --admin-password MyPg@dm1nPassw0rd \
    --public-access 1.2.3.4

az postgres db create --resource-group mypodcasts --server-name mypgserver --name mypodcasts
```

See Also:

- <https://learn.microsoft.com/en-us/azure/postgresql/single-server/quickstart-create-server-database-azure-cli>
- <https://learn.microsoft.com/en-us/azure/postgresql/single-server/quickstart-create-server-database-portal>

#### Use `psql` or Azure Data Studio or `pgadmin` to create a more restricted database user

```postgres
-- Setup the database and user
CREATE USER mypodcasts WITH PASSWORD 'MyP0dcastsPassw0rd';
GRANT ALL PRIVILEGES ON DATABASE mypodcasts TO mypodcasts;
```

#### Create an App Service

```sh
az appservice plan create --location eastus --resource-group mypodcasts \
    --name app-service-plan --is-linux --sku -F1
```

<https://learn.microsoft.com/en-us/azure/app-service/quickstart-python?tabs=flask%2Cwindows%2Cazure-portal%2Cvscode-deploy%2Cdeploy-instructions-azportal%2Cterminal-bash%2Cdeploy-instructions-zip-azcli>

#### Create Web App

```sh
az webapp create --location eastus --resource-group mypodcasts --plan app-service-plan -n mypodcasts --logs
```

#### Deploy the code in this repo to the Web App

```sh
git remote add azure $(az webapp deployment list-publishing-credentials -n mypodcasts -g mypodcasts --query scmUri -o tsv)/mypodcasts.git

git push azure master
```

#### Set some environment variables to configure the webapp

This tells it how to behave and how to connect to the db:

```sh
az webapp config appsettings set --name mypodcasts --resource-group mypodcasts --settings \
    FLASK_APP="server.py" \
    FLASK_DEBUG="0" \
    NUMBER_MAX_USER="1" \
    ADMIN_PASS="SomeSecretPassword" \
    DATABASE_URL="postgres://mypodcasts:MyP0dcastsPassw0rd@mypgserver.postgres.database.azure.com:5432/mypodcasts?sslmode=require" \
    PODCASTING_INDEX_KEY="TODO/optional" \
    PODCASTING_INDEX_SECRET="TODO/optional"
```

#### Setup Automatic CI/CD (Optional)

```sh
# Set the name of the webapp to publish to on commits:
echo 'mypodcast' | gh secret set AZURE_WEBAPP_NAME

# Set the auth info for the webapp deployment:
az webapp deployment list-publishing-profiles --name mypodcasts --resource-group mypodcasts --xml \
    | gh secret set AZURE_WEBAPP_PUBLISH_PROFILE
```

## Create account

Open the following url:  https://APP_NAME.herokuapp.com/create_user or https://YourWebAppName.azurewebsites.net

Enter your login and password.

**Please note I did not use a password recovery tool, if you forget it you will have to re-create an account. For reset delete user with request DELETE FROM account;**

## Using App

### Web

I'm not a web application developer so it's very simple. I take any help

You can access it via the url https://APP_NAME.herokuapp.com or https://YourWebAppName.azurewebsites.net

### Android

https://play.google.com/store/apps/details?id=com.ravenfeld.garmin.podcasts

At the 1st launch a login page will ask you.

1. Set url application https://APP_NAME.herokuapp.com/ or https://YourWebAppName.azurewebsites.net/
2. Set login
3. Set password
4. Enjoy

### iOS

If someone is available to help me, I am interested.

### Garmin Connect

https://apps.garmin.com/fr-FR/apps/5c22c9d7-4f38-4e03-8897-ad393b705dad

You must configure the server before using the application by indicating the url of your application

1. Open Garmin Connect IQ or Garmin Express. [Visit the documentation](https://support.garmin.com/fr-FR/?faq=SPo0TFvhQO04O36Y5TYRh5)
2. Set url application https://APP_NAME.herokuapp.com/ or https://YourWebAppName.azurewebsites.net/
3. Save
4. Select MyPodcasts as a music source on watch
5. A login page will open for your mobile on the 1st use. **Please note that the BLE connection with your watch must work**
6. Enjoy

## Question ?

Do not hesitate to send me an email to alexis.lecanu.garmin@gmail.com if you have any concerns
