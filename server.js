const express = require('express');
const path = require('path');
const fs = require('fs');
const multer = require('multer'); // File upload handler

const app = express();
const PORT = process.env.PORT || 3000;

// Setup Multer for storage
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const uploadDir = 'uploads/';
        // Create directory if it doesn't exist
        if (!fs.existsSync(uploadDir)) {
            fs.mkdirSync(uploadDir);
        }
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        cb(null, 'proposal-' + uniqueSuffix + path.extname(file.originalname));
    }
});

const upload = multer({
    storage: storage,
    limits: { fileSize: 5 * 1024 * 1024 } // 5MB limit
});

// Middleware
app.use(express.static(path.join(__dirname))); // Serve static files
app.use(express.json()); // Parse JSON bodies

// Data storage (JSON file for simplicity)
const DB_FILE = 'bookings.json';

// Helper to save data
const saveBooking = (data) => {
    let bookings = [];
    if (fs.existsSync(DB_FILE)) {
        try {
            bookings = JSON.parse(fs.readFileSync(DB_FILE));
        } catch (e) {
            console.error("Error reading JSON db", e);
        }
    }
    bookings.push({
        id: Date.now(),
        date: new Date().toISOString(),
        ...data
    });
    fs.writeFileSync(DB_FILE, JSON.stringify(bookings, null, 2));
};

// API: Handle Calculator Form (with Photos)
// Accepts multiple fields named photo1, photo2, photo3
app.post('/api/calculate', upload.fields([
    { name: 'photo1', maxCount: 1 },
    { name: 'photo2', maxCount: 1 },
    { name: 'photo3', maxCount: 1 }
]), (req, res) => {
    console.log('Received calculation request:', req.body);

    const fileData = {};
    if (req.files) {
        if (req.files.photo1) fileData.photo1 = req.files.photo1[0].path;
        if (req.files.photo2) fileData.photo2 = req.files.photo2[0].path;
        if (req.files.photo3) fileData.photo3 = req.files.photo3[0].path;
    }

    const bookingData = {
        type: 'calculation',
        ...req.body,
        photos: fileData
    };

    saveBooking(bookingData);
    res.json({ success: true, message: 'Application received' });
});

// API: Handle Footer Callback
app.post('/api/callback', (req, res) => {
    console.log('Received callback request:', req.body);

    saveBooking({
        type: 'callback',
        ...req.body
    });

    res.json({ success: true, message: 'Callback requested' });
});

// API: Admin list (simple protected endpoint)
app.get('/api/bookings', (req, res) => {
    if (fs.existsSync(DB_FILE)) {
        res.json(JSON.parse(fs.readFileSync(DB_FILE)));
    } else {
        res.json([]);
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
});
