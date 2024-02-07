#flask app implementation
import base64
import requests


def get_spotify_track_recommendations(keyword, search_type='track', limit=6):
    # Replace these values with your actual Spotify API credentials
    SPOTIFY_CLIENT_ID = 'd0c345f7c8f7437f9001583b3bdae340'
    SPOTIFY_CLIENT_SECRET = '18cf1155bba744dda945b70325ca71cc'

    # Set up your Spotify API credentials
    client_credentials = f'{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}'
    base64_credentials = base64.b64encode(client_credentials.encode('utf-8')).decode('utf-8')
    headers = {'Authorization': f'Basic {base64_credentials}'}

    # Spotify API token endpoint
    token_endpoint = 'https://accounts.spotify.com/api/token'

    # Spotify API search endpoint
    search_endpoint = 'https://api.spotify.com/v1/search'

    # Request access token
    token_response = requests.post(
        token_endpoint,
        headers=headers,
        data={'grant_type': 'client_credentials'}
    )

    # Check if the token request was successful (status code 200)
    if token_response.status_code == 200:
        # Parse the access token
        access_token = token_response.json().get('access_token')

        # Set the Authorization header with the access token
        headers['Authorization'] = f'Bearer {access_token}'

        # Make the search request with the updated headers and limit
        response = requests.get(search_endpoint, params={'q': keyword, 'type': search_type, 'limit': limit},
                                headers=headers)

        # Check if the search request was successful (status code 200)
        if response.status_code == 200:
            # Parse and return the results
            results = response.json()
            return results

        else:
            # Return an error message if the search request was not successful
            return {'error': f"Search Error: {response.status_code} - {response.text}"}

    else:
        # Return an error message if the token request was not successful
        return {'error': f"Token Error: {token_response.status_code} - {token_response.text}"}
