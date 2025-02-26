# tests/test_keychain.py

import keyring

def test_keychain_retrieval():
    """
    Test function to verify that keychain access is working properly.
    This test checks if a credential can be retrieved, but does not display the actual value.
    """
    # Define the service name and account name
    service_name = "carchive"  # The label of the entry in the macOS Keychain
    account_name = "carchive_app"  # The username associated with the password

    # Attempt to retrieve the password
    try:
        password = keyring.get_password(service_name, account_name)

        if password:
            print(f"Password successfully retrieved for '{service_name}' and account '{account_name}'")
            return True
        else:
            print(f"No password found for service '{service_name}' and account '{account_name}'.")
            return False

    except Exception as e:
        print(f"An error occurred while retrieving the password: {str(e)}")
        return False

if __name__ == "__main__":
    test_keychain_retrieval()
