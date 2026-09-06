SELECT set_config('request.jwt.claims', '{"sub":"5119fad4-171b-4b49-b88d-3aadc70a4777","role":"authenticated"}', true);
SET ROLE authenticated;
SELECT auth.uid();