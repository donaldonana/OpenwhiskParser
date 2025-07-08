1. **Set up** :

    We first need to set up **OpenWhisk**, **wsk** and **wskdeploy**, then we can test the parser with the following exemple : 


2. **definition-v0.json** : 

    we use the extended syntaxe in **definitions/definition-v0.json** to define the following workflow:

    ![Alt text](images/v0.svg) 
    
    Each fi function in this exemple just the "hello world" string.

    Use the following command to deploy the workflow. It creates the final **manifest.yaml** and directly deploys the unique sequence.
    ```bash 
        python3 -m owk.generator definitions/definition-v0.json
    ```

3. **definition-v1.json** : 

    we use the extended syntax  in **definitions/definition-v1.json** to define the following workflow : 

    ![Alt text](images/v2.svg) 

    Use the following command to deploy the workflow. It creates the final **manifest.yaml** and directly deploys all the alternative sequences.

    ```bash 
        python3 -m owk.generator definitions/definition-v1.json
    ```

3. **definition-v4.json** : 

    We use the extended syntax in **definitions/definition-v4.json** to define the following workflow:

    ![Alt text](images/v4.svg) 

    Use the following command to deploy the workflow. It creates the final **manifest.yaml** and directly deploys all the alternative sequences.

    ```bash 
        python3 -m owk.generator definitions/definition-v4.json
    ```