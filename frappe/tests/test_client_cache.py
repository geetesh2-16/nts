import time

import nts
from nts.tests import IntegrationTestCase
from nts.utils.redis_wrapper import ClientCache

TEST_KEY = "42"


class TestClientCache(IntegrationTestCase):
	def setUp(self) -> None:
		nts.client_cache.delete_value(TEST_KEY)
		return super().setUp()

	def test_client_cache_is_used(self):
		nts.client_cache.set_value(TEST_KEY, 42)
		nts.client_cache.get_value(TEST_KEY)
		with self.assertRedisCallCounts(0):
			nts.client_cache.get_value(TEST_KEY)

	def test_client_cache_is_updated_instantly_noloop(self):
		val = nts.generate_hash()
		nts.client_cache.set_value(TEST_KEY, val)
		with self.assertRedisCallCounts(0):  # Locally set value should not be invalidated.
			self.assertEqual(nts.client_cache.get_value(TEST_KEY), val)

	def test_invalidation_from_another_client_works(self):
		nts.client_cache.reset_statistics()
		val = nts.generate_hash()
		nts.client_cache.set_value(TEST_KEY, val)
		self.assertEqual(nts.client_cache.get_value(TEST_KEY), val)

		# nts.cache is our "another client"
		val = nts.generate_hash()
		nts.cache.set_value(TEST_KEY, val)
		# This is almost instant, but obviously not as fast as running the next instruction in
		# current thread. So we wait.
		time.sleep(0.1)

		with self.assertRedisCallCounts(1, exact=True):
			self.assertEqual(nts.client_cache.get_value(TEST_KEY), val)

		self.assertEqual(nts.client_cache.statistics.hits, 1)
		self.assertEqual(nts.client_cache.statistics.misses, 1)
		self.assertEqual(nts.client_cache.statistics.hit_ratio, 0.5)

	def test_delete_invalidates(self):
		val = nts.generate_hash()
		nts.client_cache.set_value(TEST_KEY, val)
		self.assertEqual(nts.client_cache.get_value(TEST_KEY), val)

		val = nts.generate_hash()
		nts.cache.delete_value(TEST_KEY)
		# This is almost instant, but obviously not as fast as running the next instruction in
		# current thread. So we wait.
		time.sleep(0.1)

		with self.assertRedisCallCounts(1, exact=True):
			self.assertIsNone(nts.client_cache.get_value(TEST_KEY))

		# Flushall should have results
		nts.client_cache.set_value(TEST_KEY, val)
		self.assertEqual(nts.client_cache.get_value(TEST_KEY), val)
		nts.cache.flushall()
		time.sleep(0.1)
		with self.assertRedisCallCounts(1, exact=True):
			self.assertIsNone(nts.client_cache.get_value(TEST_KEY))

		# nts.clear_cache should have same results
		nts.client_cache.set_value(TEST_KEY, val)
		self.assertEqual(nts.client_cache.get_value(TEST_KEY), val)
		nts.clear_cache()
		time.sleep(0.1)
		with self.assertRedisCallCounts(1, exact=True):
			self.assertIsNone(nts.client_cache.get_value(TEST_KEY))

	def test_client_local_cache_ttl(self):
		c = ClientCache(ttl=1)
		c.set_value(TEST_KEY, 42)
		with self.assertRedisCallCounts(0):
			c.get_value(TEST_KEY)
		time.sleep(1)

		with self.assertRedisCallCounts(1, exact=True):
			c.get_value(TEST_KEY)

	def test_client_cache_maxsize(self):
		c = ClientCache(maxsize=2)
		c.set_value(TEST_KEY, 42)
		c.set_value(nts.generate_hash(), 42)
		c.set_value(nts.generate_hash(), 42)

		self.assertEqual(len(c.cache), 2)

	def test_shared_keyspace(self):
		val = nts.generate_hash()
		nts.client_cache.set_value(TEST_KEY, val)

		self.assertEqual(nts.client_cache.get_value(TEST_KEY), nts.cache.get_value(TEST_KEY))

	def test_shared_keys(self):
		val = nts.generate_hash()
		nts.client_cache.set_value(TEST_KEY, val, shared=True)
		with self.assertRedisCallCounts(0):
			self.assertEqual(nts.client_cache.get_value(TEST_KEY, shared=True), val)

	def test_generator(self):
		val = nts.generate_hash()
		with self.assertRedisCallCounts(3, exact=True):
			self.assertEqual(nts.client_cache.get_value(TEST_KEY, generator=lambda: val), val)

		with self.assertRedisCallCounts(0):
			self.assertEqual(nts.client_cache.get_value(TEST_KEY, generator=lambda: val), val)

	def test_get_doc(self):
		nts.client_cache.get_doc("User", "Guest")
		with self.assertRedisCallCounts(0):
			nts.client_cache.get_doc("User", "Guest")
