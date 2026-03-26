# Добавить в класс Database (после существующих методов)

    def get_auth_hash(self) -> Optional[Dict[str, Any]]:
        """Get stored authentication hash"""
        return self.get_key('auth_hash')

    def get_encryption_salt(self) -> Optional[bytes]:
        """Get stored encryption salt"""
        key_data = self.get_key('enc_salt')
        if key_data:
            return key_data.get('salt')
        return None

    def get_key_params(self) -> Optional[Dict[str, Any]]:
        """Get key derivation parameters"""
        key_data = self.get_key('params')
        if key_data and key_data.get('params'):
            import json
            return json.loads(key_data['params'])
        return None

    def store_auth_hash(self, hash_data: str, params: Dict[str, Any]) -> int:
        """Store authentication hash"""
        import json
        return self.store_key('auth_hash', None, hash_data.encode(), json.dumps(params))

    def store_encryption_salt(self, salt: bytes) -> int:
        """Store encryption salt"""
        return self.store_key('enc_salt', salt, None, '')

    def store_key_params(self, params: Dict[str, Any]) -> int:
        """Store key derivation parameters"""
        import json
        return self.store_key('params', None, None, json.dumps(params))
