export const projectsCatalog = [
  {
    id: 'coastech',
    title: 'Coastech',
    tagline: 'Full-stack DTC ecommerce platform for modern online stores',
    summary:
      'A production-ready ecommerce platform with a Next.js storefront, Medusa commerce backend, Paystack payments, customer accounts, order tracking, and an admin operations dashboard.',
    overview:
      'Coastech is a full-stack direct-to-consumer ecommerce platform built for end-to-end online shopping operations. Customers can browse products, manage carts and accounts, complete checkout with Paystack, and track their orders from one storefront.',
    details:
      'The project combines a TypeScript and Next.js storefront with Medusa-powered commerce services. It brings together product catalog and variant selection, cart and promotion support, multi-step checkout, customer order history, payment processing, and administrative operations in one deployable system.',
    platform: 'web',
    type: 'problem-solving',
    status: 'live',
    stack: ['Next.js', 'TypeScript', 'Medusa', 'Paystack', 'PostgreSQL'],
    tags: ['Ecommerce', 'Payments', 'Next.js', 'TypeScript'],
    cardImage: '',
    gallery: [],
    links: {
      repo: 'https://github.com/mikesplore/coastech',
      demo: 'https://coastech.mikesplore.me',
    },
  },
  {
    id: 'vela-mcp',
    title: 'Vela MCP Server',
    tagline: 'MCP server exposing Vela RemotePC endpoints as tools for AI clients',
    summary:
      'MCP (Model Context Protocol) server that exposes Vela RemotePC endpoints as tools, so AI clients (Claude Desktop, Cline, Cursor, Gemini, etc.) can control remote systems. Supports STDIO (single-tenant) and HTTP (multi-tenant) transports sharing 150+ tool definitions.',
    overview:
      'Vela MCP Server bridges AI assistants with remote computer control. It exposes Vela RemotePC endpoints as Model Context Protocol tools, enabling AI clients like Claude Desktop, Cline, and Cursor to execute commands on remote machines. The server supports both STDIO for single-tenant setups and HTTP for multi-tenant deployments.',
    details:
      'The architecture consists of a FastAPI backend that translates MCP tool calls into Vela RemotePC API requests. The server maintains a registry of 150+ tool definitions covering file operations, process management, and system monitoring. Transport layer abstraction allows the same tool definitions to work across STDIO (for local AI clients) and HTTP (for cloud-hosted multi-tenant scenarios).',
    platform: 'tooling',
    type: 'problem-solving',
    status: 'source-only',
    stack: ['Python', 'FastAPI', 'MCP', 'HTTP', 'STDIO'],
    tags: ['AI', 'MCP', 'Tooling', 'Remote Control'],
    cardImage: 'https://i.ibb.co/Fktsm4DQ/vela.webp',
    gallery: [
      'https://i.ibb.co/y5TD8KW/unstacked2.jpg',
      'https://i.ibb.co/y5TD8KW/unstacked2.jpg',
      
    ],
    links: {
      repo: 'https://github.com/mikesplore/vela-mcp',
      demo: '',
    },
  },
  {
    id: 'gatekeeperd',
    title: 'Gatekeeperd',
    tagline: 'Payment gating engine for client projects hosted on your VPS',
    summary:
      'Payment gating engine for client projects hosted on your VPS. Gatekeeperd sits behind your reverse proxy (nginx or Traefik), decides whether traffic reaches a client app, and shows a self-service Paystack paywall when a project is suspended.',
    overview:
      'Gatekeeperd is a payment gating engine that sits between your reverse proxy and client applications. It intercepts incoming traffic, checks payment status, and displays a self-service Paystack paywall when a project is suspended for non-payment.',
    details:
      'Built to run behind nginx or Traefik, Gatekeeperd uses middleware to evaluate each request against a payment status database. When a project is flagged as suspended, traffic is redirected to a branded paywall page where clients can complete payment via Paystack. The system logs all access attempts and provides audit trails for billing disputes.',
    platform: 'tooling',
    type: 'problem-solving',
    status: 'live',
    stack: ['Go', 'Paystack API', 'SQLite', 'nginx', 'Traefik'],
    tags: ['Payments', 'Infrastructure'],
    cardImage: 'https://i.ibb.co/JwzrKLv1/gatekeeperd.png',
    gallery: [
      'https://i.ibb.co/4n6k3GHD/projects.png',
      'https://i.ibb.co/PzsZnQj0/containers.png',
      'https://i.ibb.co/LzVDMtxY/blocked.png'
    ],
    links: {
      repo: 'https://github.com/mikesplore/gatekeeperd',
      demo: 'https://gatekeeperd.mikesplore.me',
    },
  },
  {
    id: 'vela',
    title: 'Vela',
    tagline: 'Cross-platform remote device orchestration via natural language',
    summary:
      'Native Kotlin Android client plus a FastAPI backend that turns plain-English intents into device actions using LLM function calling.',
    overview:
      'Vela enables remote device control through natural language commands. A native Kotlin Android client communicates with a FastAPI backend that uses LLM function calling to translate plain-English intents into actionable device commands.',
    details:
      'The system architecture separates concerns between the mobile client (handling UI and local state) and the backend (processing natural language queries). The backend leverages LLM function calling to parse user intents and route them to appropriate device action handlers. This design allows for extensible command sets without modifying the client application.',
    platform: 'android',
    type: 'problem-solving',
    status: 'source-only',
    stack: ['Kotlin', 'Python', 'FastAPI', 'LLM Function Calling'],
    tags: ['Android', 'AI', 'Remote Control', 'NLP'],
    cardImage: 'https://i.ibb.co/Fktsm4DQ/vela.webp',
    gallery: [
      '/projects/vela/screenshot-1.png',
      '/projects/vela/screenshot-2.png',
    ],
    links: {
      repo: 'https://github.com/mikesplore/vela',
      demo: '',
    },
  },
  {
    id: 'tessera',
    title: 'Tessera',
    tagline: 'Automated institutional timetable management and scheduling engine',
    summary:
      'A timetable management system for academic institutions that allows students to view schedules, lecturers to manage qualifications, and administrative staff to organize academic scheduling.',
    overview:
      'Tessera automates timetable management for academic institutions. Students can view their class schedules, lecturers manage their qualifications and availability, and administrative staff organize complex academic scheduling constraints.',
    details:
      'The system implements a constraint-satisfaction algorithm to generate conflict-free timetables. Key features include role-based access control (students, lecturers, admins), real-time schedule updates, and integration with existing student information systems. The scheduling engine handles room capacity, lecturer availability, and course prerequisites.',
    platform: 'web',
    type: 'problem-solving',
    status: 'live',
    stack: ['Django', 'PostgreSQL', 'JavaScript', 'Constraint Satisfaction'],
    tags: ['Education', 'Scheduling', 'Web App'],
    cardImage: 'https://i.ibb.co/Mkx4D15n/tessera.png',
    gallery: [
      '/projects/tessera/screenshot-1.png',
      '/projects/tessera/screenshot-2.png',
    ],
    links: {
      repo: 'https://github.com/mikesplore/tessera',
      demo: 'https://timetable.mikesplore.tech',
    },
  },
  {
    id: 'quickscore',
    title: 'QuickScore',
    tagline: 'AI-Powered Instant Loan Assessment Platform',
    summary:
      'A modern fintech application built with Next.js and powered by Google Gemini AI that leverages artificial intelligence to provide instant credit assessments and loan decisions in minutes.',
    overview:
      'QuickScore is an AI-powered fintech platform that provides instant credit assessments. Built with Next.js and Google Gemini AI, it analyzes applicant data to deliver loan decisions within minutes.',
    details:
      'Hackathon project built in 48 hours. The system ingests financial statements and transaction history, then uses Gemini AI to extract risk signals and generate credit scores. The frontend provides a clean dashboard for loan officers to review AI recommendations alongside traditional metrics.',
    platform: 'web',
    type: 'hackathon',
    status: 'source-only',
    stack: ['Next.js', 'Google Gemini AI', 'Tailwind CSS'],
    tags: ['Fintech', 'AI', 'Hackathon'],
    cardImage: '',
    gallery: [
      '/projects/quickscore/screenshot-1.png',
      '/projects/quickscore/screenshot-2.png',
    ],
    links: {
      repo: 'https://github.com/mikesplore/QuickScore',
      demo: '',
    },
  },
  {
    id: 'tuya-smart-meter',
    title: 'Tuya Smart Meter Integration System',
    tagline: 'IoT meter management with automated M-Pesa billing pipelines',
    summary:
      'A backend system for managing Tuya Smart Meters, user accounts, meter assignments, and automated payment processing via M-Pesa.',
    overview:
      'A backend system for IoT meter management integrating Tuya Smart Meters with M-Pesa payment processing. Handles user accounts, meter assignments, and automated billing workflows.',
    platform: 'tooling',
    type: 'problem-solving',
    status: 'source-only',
    stack: ['Python', 'Tuya API', 'M-Pesa API', 'PostgreSQL'],
    tags: ['IoT', 'Payments', 'Backend'],
    cardImage: '',
    gallery: ['/projects/tuya/screenshot-1.png'],
    links: {
      repo: 'https://github.com/mikesplore/tuyampesa',
      demo: '',
    },
  },
  {
    id: 'kipepeo-intelligence',
    title: 'Kipepeo Intelligence',
    tagline: 'Credit-worthiness scoring from M-Pesa statements and usage behavior',
    summary:
      'Hackathon project focused on extracting practical borrower signals from transaction patterns lenders already understand.',
    overview:
      'Kipepeo Intelligence extracts credit-worthiness signals from M-Pesa transaction statements. The system analyzes spending patterns, income regularity, and financial behavior to generate lender-ready credit assessments.',
    details:
      'Built for the Build With AI Hackathon (winner). The ML pipeline processes M-Pesa statements to identify patterns like recurring income, bill payment consistency, and discretionary spending ratios. Features are fed into a gradient boosting model trained on historical lending outcomes.',
    platform: 'web',
    type: 'hackathon',
    status: 'source-only',
    stack: ['Python', 'scikit-learn', 'Pandas', 'Streamlit'],
    tags: ['Fintech', 'ML', 'Hackathon Winner'],
    cardImage: '',
    gallery: ['/projects/kipepeo/screenshot-1.png'],
    links: {
      repo: 'https://github.com/mikesplore/Kipepeo-Intelligence',
      demo: '',
    },
  },
  {
    id: 'git-roast-wrapped',
    title: 'Git Roast Wrapped',
    tagline: 'Brutal, AI-powered codebase comedy wrapped in a yearly review',
    summary:
      'Get ready for the most savage, AI-powered roast of your GitHub year. Spotify Wrapped vibes meet brutal coding reality checks. Swipe through beautifully designed slides showcasing your commits, repos, and languages.',
    overview:
      'Git Roast Wrapped generates AI-powered comedic roasts of your GitHub activity. Like Spotify Wrapped but for developers—it analyzes your commits, repos, and coding habits to create shareable, brutally honest slide decks.',
    details:
      'Uses the GitHub API to fetch yearly activity data, then prompts an LLM to generate humorous commentary based on patterns like commit timing, language diversity, and contribution streaks. The frontend renders results as swipeable slides optimized for social sharing.',
    platform: 'web',
    type: 'hobby',
    status: 'source-only',
    stack: ['React', 'GitHub API', 'LLM API'],
    tags: ['Fun', 'GitHub', 'AI'],
    cardImage: 'https://i.ibb.co/2bgQjGc/gitroast.png',
    gallery: ['/projects/git-roast/screenshot-1.png'],
    links: {
      repo: 'https://github.com/mikesplore/github-wrapped',
      demo: '',
    },
  },
  {
    id: 'styleai-studio',
    title: 'StyleAI Studio',
    tagline: 'Generative AI web platform for intelligent fashion visualization',
    summary:
      "A cutting-edge web application that leverages generative AI to revolutionize how users visualize and manage fashion, providing a seamless and intuitive experience powered by Google's Gemini models.",
    overview:
      'StyleAI Studio uses generative AI to help users visualize fashion concepts. Upload sketches or descriptions, and the platform generates realistic renderings powered by Google Gemini models.',
    platform: 'web',
    type: 'curiosity',
    status: 'source-only',
    stack: ['Next.js', 'Google Gemini', 'Cloudinary'],
    tags: ['Fashion', 'Generative AI', 'Creative'],
    cardImage: '',
    gallery: ['/projects/styleai/screenshot-1.png'],
    links: {
      repo: 'https://github.com/mikesplore/style-ai-studio',
      demo: '',
    },
  },
  {
    id: 'storyloom',
    title: 'StoryLoom',
    tagline: 'Interactive, multilingual AI children storytelling and learning platform',
    summary:
      'An AI-powered storytelling web app that lets users create unique, age-appropriate stories with beautiful AI-generated cover images, interactive post-reading comprehension quizzes, and vocabulary flashcards.',
    overview:
      "StoryLoom creates personalized children's stories using AI. Users input themes or characters, and the platform generates age-appropriate narratives with AI-generated cover art, comprehension quizzes, and vocabulary flashcards.",
    details:
      "Supports multiple languages and reading levels. The story generation pipeline uses prompt engineering to ensure content appropriateness, while the quiz system extracts key concepts for comprehension testing. Flashcards are generated from story vocabulary with definitions tailored to the child's age.",
    platform: 'web',
    type: 'curiosity',
    status: 'source-only',
    stack: ['React', 'LLM API', 'Image Generation API'],
    tags: ['Education', 'Children', 'AI', 'Multilingual'],
    cardImage: '',
    gallery: ['/projects/storyloom/screenshot-1.png'],
    links: {
      repo: 'https://github.com/mikesplore/StoryLoom',
      demo: '',
    },
  },
  {
    id: 'quizbase',
    title: 'QuizBase',
    tagline: 'Deterministic retrieval engine for verified flashcard verification',
    summary:
      'A retrieval-locked assistant that searches Quizlet flashcards and returns exact answers. Type a question, get the answer directly from Quizlet No AI hallucination, no external sources.',
    overview:
      'QuizBase is a deterministic Q&A engine that retrieves exact answers from Quizlet flashcards. Unlike AI assistants that may hallucinate, QuizBase only returns verified content from existing flashcard sets.',
    details:
      'Implements a search-index over Quizlet public sets. Queries are matched against stored Q&A pairs using fuzzy string matching, returning exact matches with source attribution. No generative AI means zero hallucination risk.',
    platform: 'web',
    type: 'problem-solving',
    status: 'source-only',
    stack: ['Python', 'Elasticsearch', 'Quizlet API'],
    tags: ['Education', 'Search', 'Flashcards'],
    cardImage: '',
    gallery: ['/projects/quizbase/screenshot-1.png'],
    links: {
      repo: 'https://github.com/mikesplore/QuizBase',
      demo: '',
    },
  },
  {
    id: 'student-admission-scanner',
    title: 'Student Admission Scanner',
    tagline: 'QR-based fee statement verification and audit tracking system',
    summary:
      'Scans the QR code in student fee statements to verify the data, and tracks which person scanned which student details.',
    overview:
      'An Android app that scans QR codes on student fee statements to verify payment data. The system maintains an audit trail of who scanned which student records and when.',
    details:
      'Built for university admission offices. The app decodes QR codes containing encrypted fee statement data, validates against a central database, and logs each scan with user identification. Prevents fraudulent document submissions during admission processing.',
    platform: 'android',
    type: 'problem-solving',
    status: 'source-only',
    stack: ['Kotlin', 'Android CameraX', 'QR Scanning'],
    tags: ['Android', 'Education', 'Verification'],
    cardImage: '',
    gallery: ['/projects/admission-scanner/screenshot-1.png'],
    links: {
      repo: 'https://github.com/mikesplore/StudentAdmissionScanner',
      demo: '',
    },
  },
  {
    id: 'ai-machine-recommender',
    title: 'AI Machine Recommender',
    tagline: 'Context-aware hardware analysis and recommendation engine',
    summary:
      'A web-based AI-powered recommendation system for laptops and computers. Users provide their requirements, budget, and preferences, and the AI analyzes available machines to provide personalized recommendations.',
    overview:
      'An AI system that recommends laptops and computers based on user requirements. Input your use case, budget, and preferences—the engine analyzes available options and returns personalized hardware recommendations.',
    platform: 'web',
    type: 'curiosity',
    status: 'source-only',
    stack: ['Python', 'scikit-learn', 'Flask'],
    tags: ['AI', 'Hardware', 'Recommendations'],
    cardImage: '',
    gallery: ['/projects/machine-recommender/screenshot-1.png'],
    links: {
      repo: '',
      demo: '',
    },
  },
  {
    id: 'uni-connect',
    title: 'Uni Connect',
    tagline: 'Unified campus hub for student coordination and resource allocation',
    summary:
      'A comprehensive student management app that facilitates resource sharing, discussions, attendance tracking, announcements, and access to course materials.',
    overview:
      'Uni Connect is a campus-wide student management platform. Features include resource sharing, discussion forums, attendance tracking, announcements, and centralized access to course materials.',
    details:
      'Designed to replace fragmented communication channels (WhatsApp groups, email chains) with a unified platform. Role-based permissions separate students, lecturers, and admins. Push notifications ensure timely delivery of announcements and deadline reminders.',
    platform: 'android',
    type: 'hobby',
    status: 'source-only',
    stack: ['Kotlin', 'Firebase', 'Jetpack Compose'],
    tags: ['Android', 'Education', 'Community'],
    cardImage: '',
    gallery: ['/projects/uni-connect/screenshot-1.png'],
    links: {
      repo: 'https://github.com/mikesplore/Uni-Connect',
      demo: '',
    },
  },
];
