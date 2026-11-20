"""
Connection & Authentication Test Script for Navia Trading API.
Use this script to verify your credentials and API connectivity before running algos.
"""

import sys
import config
from navia import NaviaClient


def run_test():
    print("=" * 60)
    print("🚀 Navia Trading API Connection Verification")
    print("=" * 60)
    print(f"Base URL:       {config.NAVIA_BASE_URL}")
    print(f"Client Code:    {config.NAVIA_CLIENT_CODE or '[NOT SET]'}")
    print(f"Trading Mode:   {'PAPER TRADING (Simulation)' if config.PAPER_TRADING else 'LIVE TRADING'}")
    print("=" * 60)

    # Initialize client
    client = NaviaClient(
        client_code=config.NAVIA_CLIENT_CODE,
        password=config.NAVIA_PASSWORD,
        api_key=config.NAVIA_API_KEY,
        auth_token=config.NAVIA_AUTH_TOKEN,
        base_url=config.NAVIA_BASE_URL,
        paper_trading=config.PAPER_TRADING,
    )

    if config.PAPER_TRADING:
        print("\n✅ Paper Trading Mode is ACTIVE.")
        print("Testing virtual order placement and portfolio...")

        # Test simulated order
        order = client.place_order(
            symbol="RELIANCE-EQ",
            exchange="NSE",
            side="BUY",
            qty=5,
            product="MIS",
            order_type="MKT",
        )
        print(f"Simulated Order Placed: {order}")

        # Check virtual positions
        positions = client.get_positions()
        print(f"Simulated Positions: {positions}")

        # Check virtual limits
        limits = client.get_limits()
        print(f"Simulated Limits: {limits}")

        print("\n🎉 Paper Trading Test Completed Successfully!")
        return

    # Live Mode Checks
    if not config.NAVIA_CLIENT_CODE or not config.NAVIA_PASSWORD:
        print("\n⚠️  Please configure NAVIA_CLIENT_CODE and NAVIA_PASSWORD in .env")
        print("Copy .env.example to .env and fill in your details.")
        sys.exit(1)

    print("\nAttempting Authentication with Navia Gateway...")
    try:
        if config.NAVIA_AUTH_TOKEN and config.NAVIA_AUTH_TOKEN != "DEFAULT":
            print("Using existing NAVIA_AUTH_TOKEN from configuration.")
        else:
            print("Step 1: Sending OTP...")
            otp_res = client.send_otp()
            print(f"Response: {otp_res}")

            otp = input("\nEnter OTP received on your mobile/email (or press Enter to skip): ").strip()
            if otp:
                verify_res = client.verify_otp(otp)
                print(f"Verify Response: {verify_res}")
                print(f"Captured AuthToken: {client.auth_token}")

        # Fetch Limits
        print("\nStep 2: Fetching Account Limits & Margins...")
        limits = client.get_limits()
        print(f"Limits: {limits}")

        # Fetch Order Book
        print("\nStep 3: Fetching Order Book...")
        orders = client.get_order_book()
        print(f"Open Orders Count: {len(orders)}")

        print("\n✅ Navia API Connectivity Verified Successfully!")

    except Exception as e:
        print(f"\n❌ Error connecting to Navia API: {e}")
        print("Please check your network, credentials, or server status.")


if __name__ == "__main__":
    run_test()
