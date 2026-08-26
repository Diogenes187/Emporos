INSERT INTO auth_user_account(public_id,email,display_name,password_hash,account_status)
VALUES('00000000-0000-4000-8000-000000000001','local@emporos.invalid','Local Referee','local-only-no-password','active')
ON CONFLICT(email) DO NOTHING;
