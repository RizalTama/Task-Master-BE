# Rencana Eksekusi Pembuatan Aplikasi Flutter: Task Master

Ini adalah dokumen rencana untuk memandu Gemini CLI dalam membangun aplikasi Flutter untuk proyek Task Master.

## Tahap 1: Setup Proyek Awal

1.  **Buat Proyek Flutter Baru**
    -   Masuk ke direktori `FLUTTER`.
    -   Hapus file `task_master.dart` yang sudah ada jika tidak diperlukan.
    -   Buat proyek baru dengan nama `task_master_app`.
    -   Perintah:
        ```bash
        cd FLUTTER
        rm task_master.dart
        flutter create task_master_app
        cd task_master_app
        ```

2.  **Tambahkan Dependensi ke `pubspec.yaml`**
    -   Jalankan perintah berikut untuk menambahkan semua library yang dibutuhkan.
    -   Perintah:
        ```bash
        flutter pub add provider http firebase_core firebase_auth intl
        ```

3.  **Konfigurasi Firebase**
    -   **PENTING (Aksi oleh User):** Dokumen ini mengasumsikan user akan menempatkan file `google-services.json` (untuk Android) dan `GoogleService-Info.plist` (untuk iOS) di lokasi yang benar sesuai panduan Firebase. Gemini CLI tidak bisa melakukan ini.

## Tahap 2: Struktur Folder

Buat struktur folder di dalam direktori `lib` untuk mengorganisir kode.

-   Perintah:
    ```bash
    mkdir -p lib/src/screens lib/src/widgets lib/src/services lib/src/providers lib/src/models
    ```

## Tahap 3: Penulisan Kode

Tulis file-file berikut secara berurutan.

---

### File 1: `lib/main.dart`
-   **Tujuan:** Entry point aplikasi, inisialisasi Firebase, setup Provider, dan routing.
-   **Kode:**
    ```dart
    import 'package:flutter/material.dart';
    import 'package:firebase_core/firebase_core.dart';
    import 'package:provider/provider.dart';
    import 'package:task_master_app/src/providers/auth_provider.dart';
    import 'package:task_master_app/src/screens/auth_gate.dart';

    void main() async {
      WidgetsFlutterBinding.ensureInitialized();
      await Firebase.initializeApp(); // Tambahkan konfigurasi options jika perlu
      runApp(const MyApp());
    }

    class MyApp extends StatelessWidget {
      const MyApp({super.key});

      @override
      Widget build(BuildContext context) {
        return ChangeNotifierProvider(
          create: (context) => AuthProvider(),
          child: MaterialApp(
            title: 'Task Master',
            theme: ThemeData(
              primarySwatch: Colors.indigo,
              visualDensity: VisualDensity.adaptivePlatformDensity,
            ),
            home: const AuthGate(),
          ),
        );
      }
    }
    ```

---

### File 2: `lib/src/services/api_service.dart`
-   **Tujuan:** Mengelola semua panggilan HTTP ke backend FastAPI.
-   **Kode:**
    ```dart
    import 'dart:convert';
    import 'package:http/http.dart' as http;

    class ApiService {
      final String _baseUrl = "http://127.0.0.1:8000"; // Ganti jika base URL berbeda
      final String _token;

      ApiService(this._token);

      Map<String, String> get _headers => {
            'Content-Type': 'application/json; charset=UTF-8',
            'Authorization': 'Bearer $_token',
          };

      Future<Map<String, dynamic>> postChat(String message) async {
        // Endpoint chat mengharapkan form data, bukan JSON
        final response = await http.post(
          Uri.parse('$_baseUrl/chat?user_message=$message'), // Kirim sebagai query param
          headers: {'Authorization': 'Bearer $_token'},
        );
        if (response.statusCode == 200) {
          return json.decode(utf8.decode(response.bodyBytes));
        } else {
          throw Exception('Failed to post chat: ${response.body}');
        }
      }

      Future<List<dynamic>> getAllTasks() async {
        final response = await http.get(Uri.parse('$_baseUrl/tasks'), headers: _headers);
        if (response.statusCode == 200) {
          return json.decode(utf8.decode(response.bodyBytes));
        } else {
          throw Exception('Failed to get tasks');
        }
      }

      Future<List<dynamic>> getActiveTasks() async {
        final response = await http.get(Uri.parse('$_baseUrl/tasks/active'), headers: _headers);
        if (response.statusCode == 200) {
          return json.decode(utf8.decode(response.bodyBytes));
        } else {
          throw Exception('Failed to get active tasks');
        }
      }
      
      Future<List<dynamic>> getProjects() async {
        final response = await http.get(Uri.parse('$_baseUrl/tasks/projects'), headers: _headers);
        if (response.statusCode == 200) {
          return json.decode(utf8.decode(response.bodyBytes));
        } else {
          throw Exception('Failed to get projects');
        }
      }

      Future<bool> createTask(String description, {String? dueDate, String? projectName}) async {
        final response = await http.post(
          Uri.parse('$_baseUrl/tasks'),
          headers: _headers,
          body: json.encode({
            'description': description,
            'due_date': dueDate,
            'project_name': projectName,
          }),
        );
        if (response.statusCode == 200) {
          return json.decode(response.body)['success'] ?? false;
        }
        return false;
      }
    }
    ```

---

### File 3: `lib/src/providers/auth_provider.dart`
-   **Tujuan:** Mengelola state otentikasi user.
-   **Kode:**
    ```dart
    import 'package:flutter/material.dart';
    import 'package:firebase_auth/firebase_auth.dart';
    import 'package:task_master_app/src/services/api_service.dart';

    class AuthProvider with ChangeNotifier {
      final FirebaseAuth _auth = FirebaseAuth.instance;
      User? _user;
      ApiService? _apiService;

      User? get user => _user;
      ApiService? get apiService => _apiService;
      bool get isAuthenticated => _user != null;

      AuthProvider() {
        _auth.authStateChanges().listen(_onAuthStateChanged);
      }

      Future<void> _onAuthStateChanged(User? user) async {
        _user = user;
        if (user != null) {
          final token = await user.getIdToken();
          _apiService = ApiService(token);
        } else {
          _apiService = null;
        }
        notifyListeners();
      }

      Future<void> signIn(String email, String password) async {
        try {
          await _auth.signInWithEmailAndPassword(email: email, password: password);
        } catch (e) {
          rethrow;
        }
      }

      Future<void> signUp(String email, String password) async {
        try {
          await _auth.createUserWithEmailAndPassword(email: email, password: password);
        } catch (e) {
          rethrow;
        }
      }

      Future<void> signOut() async {
        await _auth.signOut();
      }
    }
    ```

---

### File 4: `lib/src/screens/auth_gate.dart`
-   **Tujuan:** "Gerbang" yang mengecek apakah user sudah login atau belum.
-   **Kode:**
    ```dart
    import 'package:flutter/material.dart';
    import 'package:provider/provider.dart';
    import 'package:task_master_app/src/providers/auth_provider.dart';
    import 'package:task_master_app/src/screens/home_screen.dart';
    import 'package:task_master_app/src/screens/login_screen.dart';

    class AuthGate extends StatelessWidget {
      const AuthGate({super.key});

      @override
      Widget build(BuildContext context) {
        return Consumer<AuthProvider>(
          builder: (context, authProvider, child) {
            if (authProvider.isAuthenticated) {
              return const HomeScreen();
            } else {
              return const LoginScreen();
            }
          },
        );
      }
    }
    ```

---

### File 5: `lib/src/screens/login_screen.dart`
-   **Tujuan:** UI dan logika untuk login & registrasi.
-   **Kode:**
    ```dart
    import 'package:flutter/material.dart';
    import 'package:provider/provider.dart';
    import 'package:task_master_app/src/providers/auth_provider.dart';

    class LoginScreen extends StatefulWidget {
      const LoginScreen({super.key});

      @override
      _LoginScreenState createState() => _LoginScreenState();
    }

    class _LoginScreenState extends State<LoginScreen> {
      final _formKey = GlobalKey<FormState>();
      String _email = '';
      String _password = '';
      bool _isLogin = true;
      bool _isLoading = false;

      void _trySubmit() async {
        final isValid = _formKey.currentState?.validate();
        if (isValid != true) return;
        _formKey.currentState?.save();

        setState(() {
          _isLoading = true;
        });

        try {
          final authProvider = Provider.of<AuthProvider>(context, listen: false);
          if (_isLogin) {
            await authProvider.signIn(_email, _password);
          } else {
            await authProvider.signUp(_email, _password);
          }
        } catch (error) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(error.toString()),
              backgroundColor: Colors.red,
            ),
          );
        } finally {
          if (mounted) {
            setState(() {
              _isLoading = false;
            });
          }
        }
      }

      @override
      Widget build(BuildContext context) {
        return Scaffold(
          appBar: AppBar(title: Text(_isLogin ? 'Login' : 'Sign Up')),
          body: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      key: const ValueKey('email'),
                      validator: (value) => (value == null || !value.contains('@')) ? 'Please enter a valid email.' : null,
                      onSaved: (value) => _email = value ?? '',
                      keyboardType: TextInputType.emailAddress,
                      decoration: const InputDecoration(labelText: 'Email Address'),
                    ),
                    TextFormField(
                      key: const ValueKey('password'),
                      validator: (value) => (value == null || value.length < 6) ? 'Password must be at least 6 characters.' : null,
                      onSaved: (value) => _password = value ?? '',
                      obscureText: true,
                      decoration: const InputDecoration(labelText: 'Password'),
                    ),
                    const SizedBox(height: 20),
                    if (_isLoading)
                      const CircularProgressIndicator()
                    else
                      ElevatedButton(
                        onPressed: _trySubmit,
                        child: Text(_isLogin ? 'Login' : 'Sign Up'),
                      ),
                    TextButton(
                      onPressed: () {
                        setState(() {
                          _isLogin = !_isLogin;
                        });
                      },
                      child: Text(_isLogin ? 'Create new account' : 'I already have an account'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      }
    }
    ```

---

### File 6: `lib/src/screens/home_screen.dart`
-   **Tujuan:** Halaman utama dengan Bottom Navigation Bar.
-   **Kode:**
    ```dart
    import 'package:flutter/material.dart';
    import 'package:task_master_app/src/screens/tasks_list_screen.dart';
    import 'package:task_master_app/src/screens/chat_screen.dart';
    import 'package:task_master_app/src/screens/projects_screen.dart';
    import 'package:task_master_app/src/screens/add_task_screen.dart';

    class HomeScreen extends StatefulWidget {
      const HomeScreen({super.key});

      @override
      _HomeScreenState createState() => _HomeScreenState();
    }

    class _HomeScreenState extends State<HomeScreen> {
      int _selectedIndex = 0;

      static const List<Widget> _widgetOptions = <Widget>[
        TasksListScreen(mode: TaskScreenMode.all),
        TasksListScreen(mode: TaskScreenMode.active),
        ProjectsScreen(),
        ChatScreen(),
      ];

      void _onItemTapped(int index) {
        setState(() {
          _selectedIndex = index;
        });
      }

      @override
      Widget build(BuildContext context) {
        return Scaffold(
          appBar: AppBar(
            title: const Text('Task Master'),
          ),
          body: Center(
            child: _widgetOptions.elementAt(_selectedIndex),
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: () {
              Navigator.of(context).push(MaterialPageRoute(builder: (context) => const AddTaskScreen()));
            },
            child: const Icon(Icons.add),
          ),
          bottomNavigationBar: BottomNavigationBar(
            items: const <BottomNavigationBarItem>[
              BottomNavigationBarItem(icon: Icon(Icons.list), label: 'All'),
              BottomNavigationBarItem(icon: Icon(Icons.check_circle), label: 'Active'),
              BottomNavigationBarItem(icon: Icon(Icons.workspaces), label: 'Projects'),
              BottomNavigationBarItem(icon: Icon(Icons.chat), label: 'Chat AI'),
            ],
            currentIndex: _selectedIndex,
            selectedItemColor: Colors.indigo,
            unselectedItemColor: Colors.grey,
            onTap: _onItemTapped,
          ),
        );
      }
    }
    ```

---

### File 7: `lib/src/screens/tasks_list_screen.dart`
-   **Tujuan:** Menampilkan daftar tugas (bisa mode 'semua' atau 'aktif').
-   **Kode:**
    ```dart
    import 'package:flutter/material.dart';
    import 'package:provider/provider.dart';
    import 'package:task_master_app/src/providers/auth_provider.dart';

    enum TaskScreenMode { all, active }

    class TasksListScreen extends StatefulWidget {
      final TaskScreenMode mode;
      const TasksListScreen({super.key, required this.mode});

      @override
      _TasksListScreenState createState() => _TasksListScreenState();
    }

    class _TasksListScreenState extends State<TasksListScreen> {
      late Future<List<dynamic>> _tasksFuture;

      @override
      void initState() {
        super.initState();
        _loadTasks();
      }
      
      void _loadTasks() {
          final apiService = Provider.of<AuthProvider>(context, listen: false).apiService;
          if (apiService != null) {
              setState(() {
                _tasksFuture = widget.mode == TaskScreenMode.all
                    ? apiService.getAllTasks()
                    : apiService.getActiveTasks();
              });
          }
      }

      @override
      Widget build(BuildContext context) {
        return FutureBuilder<List<dynamic>>(
          future: _tasksFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            } else if (snapshot.hasError) {
              return Center(child: Text('Error: ${snapshot.error}'));
            } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
              return const Center(child: Text('No tasks found.'));
            }

            final tasks = snapshot.data!;
            return RefreshIndicator(
              onRefresh: () async {
                  _loadTasks();
              },
              child: ListView.builder(
                itemCount: tasks.length,
                itemBuilder: (context, index) {
                  final task = tasks[index] as Map<String, dynamic>;
                  return ListTile(
                    title: Text(task['description'] ?? 'No description'),
                    subtitle: Text('Project: ${task['project_name'] ?? 'N/A'} - Due: ${task['due_date'] ?? 'N/A'}'),
                    trailing: Text(task['status'] ?? ''),
                  );
                },
              ),
            );
          },
        );
      }
    }
    ```
    
---
### File 8: `lib/src/screens/projects_screen.dart`
-   **Tujuan:** Menampilkan daftar project.
-   **Kode:**
    ```dart
    import 'package:flutter/material.dart';
    import 'package:provider/provider.dart';
    import 'package:task_master_app/src/providers/auth_provider.dart';

    class ProjectsScreen extends StatefulWidget {
      const ProjectsScreen({super.key});

      @override
      State<ProjectsScreen> createState() => _ProjectsScreenState();
    }

    class _ProjectsScreenState extends State<ProjectsScreen> {
      late Future<List<dynamic>> _projectsFuture;

      @override
      void initState() {
        super.initState();
        final apiService = Provider.of<AuthProvider>(context, listen: false).apiService;
        if(apiService != null) {
          _projectsFuture = apiService.getProjects();
        }
      }

      @override
      Widget build(BuildContext context) {
        return FutureBuilder<List<dynamic>>(
          future: _projectsFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            } else if (snapshot.hasError) {
              return Center(child: Text('Error: ${snapshot.error}'));
            } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
              return const Center(child: Text('No projects found.'));
            }

            final projects = snapshot.data!;
            return ListView.builder(
              itemCount: projects.length,
              itemBuilder: (context, index) {
                final project = projects[index];
                return ListTile(
                  title: Text(project['name'] ?? 'No Name'),
                  trailing: Text('${project['task_count']} tasks'),
                );
              },
            );
          },
        );
      }
    }
    ```

---
### File 9: `lib/src/screens/add_task_screen.dart`
-   **Tujuan:** Form untuk menambah task baru.
-   **Kode:**
    ```dart
    import 'package:flutter/material.dart';
    import 'package:provider/provider.dart';
    import 'package:task_master_app/src/providers/auth_provider.dart';
    import 'package:intl/intl.dart';

    class AddTaskScreen extends StatefulWidget {
      const AddTaskScreen({super.key});

      @override
      _AddTaskScreenState createState() => _AddTaskScreenState();
    }

    class _AddTaskScreenState extends State<AddTaskScreen> {
      final _formKey = GlobalKey<FormState>();
      String _description = '';
      String? _projectName;
      DateTime? _dueDate;
      final _dateController = TextEditingController();
      bool _isLoading = false;

      Future<void> _selectDate(BuildContext context) async {
        final DateTime? picked = await showDatePicker(
          context: context,
          initialDate: _dueDate ?? DateTime.now(),
          firstDate: DateTime(2000),
          lastDate: DateTime(2101),
        );
        if (picked != null && picked != _dueDate) {
          setState(() {
            _dueDate = picked;
            _dateController.text = DateFormat.yMMMd().format(_dueDate!);
          });
        }
      }

      void _submitForm() async {
        if (!_formKey.currentState!.validate()) return;
        _formKey.currentState!.save();

        setState(() => _isLoading = true);

        final apiService = Provider.of<AuthProvider>(context, listen: false).apiService;
        final success = await apiService?.createTask(
          _description,
          dueDate: _dueDate?.toIso8601String(),
          projectName: _projectName,
        );

        setState(() => _isLoading = false);

        if (success == true) {
          Navigator.of(context).pop();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Failed to create task.'), backgroundColor: Colors.red),
          );
        }
      }

      @override
      void dispose() {
        _dateController.dispose();
        super.dispose();
      }

      @override
      Widget build(BuildContext context) {
        return Scaffold(
          appBar: AppBar(title: const Text('Add New Task')),
          body: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Form(
              key: _formKey,
              child: ListView(
                children: [
                  TextFormField(
                    decoration: const InputDecoration(labelText: 'Description'),
                    validator: (value) => (value == null || value.isEmpty) ? 'Description cannot be empty.' : null,
                    onSaved: (value) => _description = value!,
                  ),
                  TextFormField(
                    decoration: const InputDecoration(labelText: 'Project Name (Optional)'),
                    onSaved: (value) => _projectName = value,
                  ),
                  TextFormField(
                    controller: _dateController,
                    decoration: const InputDecoration(
                      labelText: 'Due Date (Optional)',
                      suffixIcon: Icon(Icons.calendar_today),
                    ),
                    readOnly: true,
                    onTap: () => _selectDate(context),
                  ),
                  const SizedBox(height: 20),
                  if (_isLoading)
                    const CircularProgressIndicator()
                  else
                    ElevatedButton(
                      onPressed: _submitForm,
                      child: const Text('Save Task'),
                    ),
                ],
              ),
            ),
          ),
        );
      }
    }
    ```

---
### File 10: `lib/src/screens/chat_screen.dart`
-   **Tujuan:** UI untuk berinteraksi dengan Chat AI.
-   **Kode:**
    ```dart
    import 'package:flutter/material.dart';
    import 'package:provider/provider.dart';
    import 'package:task_master_app/src/providers/auth_provider.dart';

    class ChatScreen extends StatefulWidget {
      const ChatScreen({super.key});

      @override
      _ChatScreenState createState() => _ChatScreenState();
    }

    class _ChatScreenState extends State<ChatScreen> {
      final _controller = TextEditingController();
      final List<Map<String, String>> _messages = [];
      bool _isLoading = false;

      void _sendMessage() async {
        final message = _controller.text;
        if (message.isEmpty) return;

        setState(() {
          _messages.add({'role': 'user', 'content': message});
          _isLoading = true;
        });
        _controller.clear();

        try {
          final apiService = Provider.of<AuthProvider>(context, listen: false).apiService;
          final response = await apiService!.postChat(message);

          setState(() {
            _messages.add({'role': 'assistant', 'content': response['reply'] ?? 'Sorry, I had a problem.'});
          });
        } catch (e) {
          setState(() {
            _messages.add({'role': 'assistant', 'content': 'Error: ${e.toString()}'});
          });
        } finally {
          setState(() {
            _isLoading = false;
          });
        }
      }

      @override
      Widget build(BuildContext context) {
        return Column(
          children: [
            Expanded(
              child: ListView.builder(
                itemCount: _messages.length,
                itemBuilder: (context, index) {
                  final msg = _messages[index];
                  bool isUser = msg['role'] == 'user';
                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: isUser ? Colors.indigo[400] : Colors.grey[200],
                        borderRadius: BorderRadius.circular(15),
                      ),
                      child: Text(
                        msg['content']!,
                        style: TextStyle(color: isUser ? Colors.white : Colors.black),
                      ),
                    ),
                  );
                },
              ),
            ),
            if (_isLoading) const Padding(padding: EdgeInsets.all(8.0), child: CircularProgressIndicator()),
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: const InputDecoration(hintText: 'Ask me to do something...'),
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: _sendMessage,
                  ),
                ],
              ),
            ),
          ],
        );
      }
    }
    ```

## Tahap 4: Menjalankan Aplikasi

Setelah semua file ditulis, jalankan aplikasi di emulator.
-   **Perintah:**
    ```bash
    flutter run
    ```
---
**Akhir dari Rencana Eksekusi.**
---
