
As part of the GreenFaas project we needed to extend language model syntax proposed by Seb's to take into account <br /> notion of alternative and parallel execution 
To use the paser propose, follow the following steps : 

1. **Set up** :

    Ensure you already have **OpenWhisk**, **wsk** and **wskdeploy** set up in your environnement : 


2. **Exemple 1: definition-v0.json** : 

    we use the extended syntaxe in **definitions/definition-v0.json** to define the following workflow:

    ![Alt text](images/v0.svg) 
    
    Each fi function in this exemple just the "hello world" string.

    Use the following command to deploy the workflow.  <br /> 
    The command will create  the final **manifest.yaml** and directly deploys the unique sequence.
    ```bash 
        python3 -m owk.generator definitions/definition-v0.json
    ```

3. **Exemple 2: definition-v1.json** : 

    **definitions/definition-v1.json** file defined the following workflow : 

    ![Alt text](images/v2.svg) 

    Use the following command to deploy the workflow.  <br /> The command will create  the final  **manifest.yaml** and directly deploys all the alternative sequences.

    ```bash 
        python3 -m owk.generator definitions/definition-v1.json
    ```

3. **Exemple 3: definition-v4.json** : 

    **definitions/definition-v4.json** file defined the following workflow :

    ![Alt text](images/v4.svg) 

    Use the following command to deploy the workflow.  <br /> The command will create  the final  **manifest.yaml** and directly deploys all the alternative sequences.

    ```bash 
        python3 -m owk.generator definitions/definition-v4.json
    ```