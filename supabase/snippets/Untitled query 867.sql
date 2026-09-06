SELECT policyname, cmd, roles, with_check
FROM pg_policies
WHERE tablename = 'objects' AND schemaname = 'storage'
