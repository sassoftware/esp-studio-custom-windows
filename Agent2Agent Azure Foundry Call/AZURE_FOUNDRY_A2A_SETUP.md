# Configure an Azure AI Foundry Agent for ESP A2A

This guide describes how to create and publish an Azure AI Foundry agent, configure its Agent2Agent (A2A) endpoint, and create Microsoft Entra application credentials. It also teaches you how to grant access to the Foundry project and configure an ESP project.

## 1. Create the Azure AI Foundry Agent

1. Open your Azure AI Foundry project.
2. Build an agent.
3. In the name field, enter a unique name.
4. In the instructions field, enter the system prompt.
5. Select an appropriate model.
6. (Optional) Test the agent using the chat pane.
7. Click **Save**.
8. Click **Publish**.

## 2. Configure the A2A Protocol

1. Open the agent's **Details** page.
2. Click **Set up** under the **A2A protocol** section.
3. In the name field, enter a name for the agent card.
4. In the description field, enter a description of the agent.
5. In the skill name field, enter the agent's intended skill or purpose.
5. Click **Save**.
6. In the **A2A protocol** section, copy the endpoint.

The endpoint is the value required to connect SAS Event Stream Processing to the Foundry agent. The Foundry agent display name does not need to be copied into the ESP project.

## 3. Create a Microsoft Entra Application Registration

1. From the Azure portal, open **Microsoft Entra ID**.
2. Expand **Manage** and select **App registrations**.
3. Click **New registration**.
4. In the name field, enter a name for the application. Use a name that is similar to the Foundry agent name to make it easier to identify.
5. Click **Register**.
6. In the left pane, select **Overview**.
7. Copy the following values from the application's overview page:
   - Application (client) ID
   - Directory (tenant) ID
8. Expand **Manage** and select **Certificates & secrets**.
9. Click **New client secret**.
10. In the description field, enter a brief description.
11. Click **Add**.
12. Copy the information under the **Value** column.

The secret value is displayed only once. Make sure to copy the **Value** and not the **Secret ID**.

## 4. Grant the Application Access to the Foundry Project

1. Open the Azure AI Foundry project in the Azure portal (for example, `proj-default`).
2. From the search bar, open **Access control (IAM)**.
3. From the **Add** drop-down, select **Add role assignment**.
4. From the table, select the **Foundry User** role.
5. Select the **Members** tab.
6. Click **Select members** and search for the application registration created earlier.
7. Add the application as a member.
8. Select the **Review + assign** tab and click the **Review + assign** button. The role assignment can take some time to propagate.
