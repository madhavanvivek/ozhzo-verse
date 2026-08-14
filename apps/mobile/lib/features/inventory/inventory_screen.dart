import 'package:flutter/material.dart';
import '../../generated/api_models.dart';

class InventoryScreen extends StatefulWidget {
  final String homeId;

  const InventoryScreen({Key? key, required this.homeId}) : super(key: key);

  @override
  State<InventoryScreen> createState() => _InventoryScreenState();
}

class _InventoryScreenState extends State<InventoryScreen> {
  String _selectedTab = 'ALL'; // ALL, CONSUMABLES, ASSETS, BORROWED
  String _searchQuery = '';

  final List<InventoryItemDTO> _items = [
    InventoryItemDTO(
      id: 'item-1',
      homeId: 'home-1',
      name: 'Basmati Rice',
      itemType: 'CONSUMABLE',
      categoryName: 'Pantry',
      quantity: 2.0,
      unit: 'kg',
      minThreshold: 5.0,
      preferredQuantity: 10.0,
      locationPath: 'Kitchen > Upper Cabinet',
      status: 'LOW',
    ),
    InventoryItemDTO(
      id: 'item-2',
      homeId: 'home-1',
      name: 'Cordless Drill',
      itemType: 'ASSET',
      categoryName: 'Tools',
      quantity: 1,
      unit: 'pcs',
      locationPath: 'Garage > Tool Rack',
      condition: 'EXCELLENT',
      assetStatus: 'AVAILABLE',
      status: 'GOOD',
    ),
    InventoryItemDTO(
      id: 'item-3',
      homeId: 'home-1',
      name: 'Heavy Duty Toolkit',
      itemType: 'ASSET',
      categoryName: 'Tools',
      quantity: 1,
      unit: 'pcs',
      locationPath: 'Store Room > 3rd Cupboard > Blue Box',
      condition: 'GOOD',
      assetStatus: 'BORROWED',
      currentHolderName: 'Ashraf',
      status: 'GOOD',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final filtered = _items.where((item) {
      final matchesSearch = item.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          (item.locationPath?.toLowerCase().contains(_searchQuery.toLowerCase()) ?? false) ||
          (item.currentHolderName?.toLowerCase().contains(_searchQuery.toLowerCase()) ?? false);

      if (_selectedTab == 'CONSUMABLES') return matchesSearch && item.itemType == 'CONSUMABLE';
      if (_selectedTab == 'ASSETS') return matchesSearch && item.itemType == 'ASSET';
      if (_selectedTab == 'BORROWED') return matchesSearch && item.assetStatus == 'BORROWED';
      return matchesSearch;
    }).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Home Inventory & Memory'),
        backgroundColor: const Color(0xFF0F2942),
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Search Bar
          Padding(
            padding: const EdgeInsets.all(12.0),
            child: TextField(
              decoration: InputDecoration(
                hintText: 'Search items, locations (e.g. Blue Box)...',
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12),
              ),
              onChanged: (val) => setState(() => _searchQuery = val),
            ),
          ),

          // Filter Chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(
              children: [
                ChoiceChip(
                  label: const Text('All'),
                  selected: _selectedTab == 'ALL',
                  onSelected: (_) => setState(() => _selectedTab = 'ALL'),
                ),
                const SizedBox(width: 8),
                ChoiceChip(
                  label: const Text('Consumables'),
                  selected: _selectedTab == 'CONSUMABLES',
                  onSelected: (_) => setState(() => _selectedTab = 'CONSUMABLES'),
                ),
                const SizedBox(width: 8),
                ChoiceChip(
                  label: const Text('Assets & Tools'),
                  selected: _selectedTab == 'ASSETS',
                  onSelected: (_) => setState(() => _selectedTab = 'ASSETS'),
                ),
                const SizedBox(width: 8),
                ChoiceChip(
                  label: const Text('Borrowed'),
                  selected: _selectedTab == 'BORROWED',
                  onSelected: (_) => setState(() => _selectedTab = 'BORROWED'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),

          // Items List
          Expanded(
            child: ListView.builder(
              itemCount: filtered.length,
              itemBuilder: (context, index) {
                final item = filtered[index];
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  elevation: 1,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  child: Padding(
                    padding: const EdgeInsets.all(12.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              item.name,
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                            ),
                            _buildStatusBadge(item),
                          ],
                        ),
                        const SizedBox(height: 4),
                        if (item.locationPath != null)
                          Row(
                            children: [
                              const Icon(Icons.location_on, size: 14, color: Color(0xFF0F2942)),
                              const SizedBox(width: 4),
                              Expanded(
                                child: Text(
                                  item.locationPath!,
                                  style: const TextStyle(fontSize: 12, color: Colors.black89, fontWeight: FontWeight.w500),
                                ),
                              ),
                            ],
                          ),
                        const SizedBox(height: 8),
                        if (item.itemType == 'CONSUMABLE')
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                '${item.quantity} ${item.unit}',
                                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                              ),
                              Row(
                                children: [
                                  IconButton(
                                    icon: const Icon(Icons.remove_circle_outline),
                                    onPressed: () {
                                      setState(() {
                                        // Quick consume
                                      });
                                    },
                                  ),
                                  IconButton(
                                    icon: const Icon(Icons.add_circle_outline),
                                    onPressed: () {
                                      setState(() {
                                        // Quick add
                                      });
                                    },
                                  ),
                                ],
                              ),
                            ],
                          )
                        else
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                item.assetStatus == 'BORROWED'
                                    ? 'With: ${item.currentHolderName}'
                                    : 'Condition: ${item.condition ?? "Good"}',
                                style: TextStyle(
                                  fontSize: 13,
                                  color: item.assetStatus == 'BORROWED' ? Colors.orange[800] : Colors.grey[700],
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              ElevatedButton.icon(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: item.assetStatus == 'BORROWED'
                                      ? const Color(0xFF0F2942)
                                      : Colors.grey[200],
                                  foregroundColor: item.assetStatus == 'BORROWED' ? Colors.white : Colors.black87,
                                  elevation: 0,
                                ),
                                icon: Icon(item.assetStatus == 'BORROWED' ? Icons.replay : Icons.person_add, size: 14),
                                label: Text(item.assetStatus == 'BORROWED' ? 'Return' : 'Borrow'),
                                onPressed: () {
                                  // Borrow / return sheet
                                },
                              ),
                            ],
                          ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        backgroundColor: const Color(0xFF0F2942),
        foregroundColor: Colors.white,
        child: const Icon(Icons.add),
        onPressed: () {
          // Open add item sheet
        },
      ),
    );
  }

  Widget _buildStatusBadge(InventoryItemDTO item) {
    if (item.itemType == 'CONSUMABLE') {
      Color bg = Colors.green[100]!;
      Color text = Colors.green[800]!;
      String label = 'In Stock';

      if (item.status == 'LOW') {
        bg = Colors.amber[100]!;
        text = Colors.amber[900]!;
        label = 'Low Stock';
      } else if (item.status == 'OUT_OF_STOCK') {
        bg = Colors.red[100]!;
        text = Colors.red[800]!;
        label = 'Out of Stock';
      }

      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(12)),
        child: Text(label, style: TextStyle(color: text, fontSize: 11, fontWeight: FontWeight.bold)),
      );
    } else {
      final isBorrowed = item.assetStatus == 'BORROWED';
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: isBorrowed ? Colors.amber[100] : Colors.green[100],
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(
          isBorrowed ? 'Borrowed' : 'Available',
          style: TextStyle(
            color: isBorrowed ? Colors.amber[900] : Colors.green[800],
            fontSize: 11,
            fontWeight: FontWeight.bold,
          ),
        ),
      );
    }
  }
}
